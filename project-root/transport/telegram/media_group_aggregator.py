"""
MediaGroup aggregator for Telegram photo albums.

Telegram sends each photo in an album as a separate update sharing the same
media_group_id. This module collects them and fires a single callback once
the group is complete (detected via timer-based debounce).

Architecture:
  transport handler
      │
      ▼
  MediaGroupAggregator.add(group_id, item)
      │  stores item in Redis list
      │  resets debounce timer on every new item
      │
      ▼  (debounce timer fires after _DEBOUNCE_TTL_SECONDS)
  _on_group_ready(group_id, items)
      │
      ▼
  caller-supplied callback (process all images together)

Redis keys per group:
  media_group:{group_id}        LIST  — serialised MediaGroupItem JSON
  media_group:{group_id}:lock   STRING (SETNX)  — flush-once guard
  media_group:{group_id}:seen   SET   — deduplicated message_ids

§ Requirements
  - Works with Upstash Free tier (no keyspace notifications needed).
  - Works across multiple bot instances because all state is in Redis.
  - Idempotent: duplicate updates (same message_id) are deduplicated via
    a SET of seen message IDs stored alongside the list.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# Debounce window: how long after the LAST photo arrives before we flush.
_DEBOUNCE_TTL_SECONDS: int = 3

# Hard cap: flush immediately if the group reaches this size.
_MAX_GROUP_SIZE: int = 10

# TTL for Redis keys (auto-cleanup if flush never happens)
_REDIS_KEY_TTL: int = 60

# Lua script: atomically RPUSH item + return list length.
_LUA_ADD = """
local list_key  = KEYS[1]
local item_json = ARGV[1]
local msg_id    = ARGV[2]
local seen_key  = KEYS[2]
local ttl_secs  = tonumber(ARGV[3])

-- Deduplication: skip if this message_id was already added.
if redis.call("SISMEMBER", seen_key, msg_id) == 1 then
    return redis.call("LLEN", list_key)
end
redis.call("SADD", seen_key, msg_id)
redis.call("EXPIRE", seen_key, ttl_secs)

-- Append item.
redis.call("RPUSH", list_key, item_json)
redis.call("EXPIRE", list_key, ttl_secs)

return redis.call("LLEN", list_key)
"""

# Lua script: atomically grab the list + delete it (flush-once).
_LUA_FLUSH = """
local list_key = KEYS[1]
local lock_key = KEYS[2]
local seen_key = KEYS[3]

-- Acquire flush lock (SETNX).
if redis.call("SETNX", lock_key, "1") == 0 then
    return nil
end

-- Collect data and delete ALL keys atomically.
local items = redis.call("LRANGE", list_key, 0, -1)
redis.call("DEL", list_key, lock_key, seen_key)

return items
"""


@dataclass(frozen=True)
class MediaGroupItem:
    """One photo in an album."""
    file_id: str
    message_id: int
    caption: str = ""
    lang: str = "ru"


CallbackType = Callable[[str, list[MediaGroupItem]], Awaitable[None]]


class MediaGroupAggregator:
    """
    Redis-backed aggregator for Telegram media groups.
    Uses asyncio timers instead of Redis keyspace notifications —
    compatible with Upstash Free tier.

    Usage:
        aggregator = MediaGroupAggregator(redis_client, on_group_ready)
        await aggregator.start()
        ...
        await aggregator.add(group_id, item)
        ...
        await aggregator.stop()
    """

    def __init__(
        self,
        redis,
        on_group_ready: CallbackType,
        debounce_ttl: int = _DEBOUNCE_TTL_SECONDS,
        max_group_size: int = _MAX_GROUP_SIZE,
    ) -> None:
        self._redis = redis
        self._on_group_ready = on_group_ready
        self._debounce_ttl = debounce_ttl
        self._max_group_size = max_group_size
        self._lua_add: object | None = None
        self._lua_flush: object | None = None
        # group_id -> asyncio.TimerHandle
        self._timers: dict[str, asyncio.TimerHandle] = {}

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Register Lua scripts."""
        self._lua_add   = self._redis.register_script(_LUA_ADD)
        self._lua_flush = self._redis.register_script(_LUA_FLUSH)
        logger.info("MediaGroupAggregator started")

    async def stop(self) -> None:
        """Cancel all pending timers."""
        for handle in self._timers.values():
            handle.cancel()
        self._timers.clear()
        logger.info("MediaGroupAggregator stopped")

    # ── public API ────────────────────────────────────────────────────────────

    async def add(self, group_id: str, item: MediaGroupItem) -> None:
        """
        Add one photo to the group buffer.
        Resets the debounce timer. Flushes immediately if max size reached.
        """
        list_key = f"media_group:{group_id}"
        seen_key = f"media_group:{group_id}:seen"

        length = await self._lua_add(
            keys=[list_key, seen_key],
            args=[
                json.dumps({
                    "file_id":    item.file_id,
                    "message_id": item.message_id,
                    "caption":    item.caption,
                    "lang":       item.lang,
                }),
                str(item.message_id),
                str(_REDIS_KEY_TTL),
            ],
        )

        logger.debug(
            "MediaGroup item added",
            extra={"group_id": group_id, "length": length, "file_id": item.file_id[:20]},
        )

        # Immediate flush on max size.
        if length and int(length) >= self._max_group_size:
            logger.info(
                "MediaGroup hit max size — flushing immediately",
                extra={"group_id": group_id, "size": length},
            )
            self._cancel_timer(group_id)
            asyncio.create_task(
                self._flush(group_id),
                name=f"media_group_flush_{group_id}",
            )
            return

        # Reset debounce timer.
        self._reset_timer(group_id)

    # ── internals ─────────────────────────────────────────────────────────────

    def _reset_timer(self, group_id: str) -> None:
        """Cancel existing timer and start a new one."""
        self._cancel_timer(group_id)
        loop = asyncio.get_event_loop()
        handle = loop.call_later(
            self._debounce_ttl,
            self._timer_fired,
            group_id,
        )
        self._timers[group_id] = handle

    def _cancel_timer(self, group_id: str) -> None:
        handle = self._timers.pop(group_id, None)
        if handle:
            handle.cancel()

    def _timer_fired(self, group_id: str) -> None:
        """Called by the event loop after debounce TTL. Schedules async flush."""
        self._timers.pop(group_id, None)
        logger.debug("MediaGroup debounce fired", extra={"group_id": group_id})
        asyncio.create_task(
            self._flush(group_id),
            name=f"media_group_flush_{group_id}",
        )

    async def _flush(self, group_id: str) -> None:
        """
        Atomically retrieve and delete the group from Redis, then call
        on_group_ready. Flush-once guaranteed via SETNX lock in Lua.
        """
        list_key = f"media_group:{group_id}"
        lock_key = f"media_group:{group_id}:lock"
        seen_key = f"media_group:{group_id}:seen"

        raw_items = await self._lua_flush(
            keys=[list_key, lock_key, seen_key],
            args=[],
        )

        if not raw_items:
            logger.debug("MediaGroup flush skipped (already processed)", extra={"group_id": group_id})
            return

        items: list[MediaGroupItem] = []
        for raw in raw_items:
            try:
                data = json.loads(raw)
                items.append(MediaGroupItem(
                    file_id=data["file_id"],
                    message_id=data["message_id"],
                    caption=data.get("caption", ""),
                    lang=data.get("lang", "ru"),
                ))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(
                    "MediaGroup: failed to deserialise item",
                    extra={"error": str(exc), "raw": str(raw)[:100]},
                )

        if not items:
            return

        logger.info(
            "MediaGroup flushing to callback",
            extra={"group_id": group_id, "count": len(items)},
        )

        try:
            await self._on_group_ready(group_id, items)
        except Exception as exc:
            logger.error(
                "MediaGroup on_group_ready callback crashed",
                extra={"group_id": group_id, "error": str(exc)},
            )