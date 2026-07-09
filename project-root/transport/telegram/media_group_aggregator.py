"""
MediaGroup aggregator for Telegram photo albums.

Telegram sends each photo in an album as a separate update sharing the same
media_group_id. This module collects them and fires a single callback once
the group is complete (detected via Redis TTL debounce).

Architecture:
  transport handler
      │
      ▼
  MediaGroupAggregator.add(group_id, item)
      │  stores item in Redis list
      │  resets debounce TTL on every new item
      │
      ▼  (TTL expires → keyspace event)
  _on_group_ready(group_id, items)
      │
      ▼
  caller-supplied callback (process all images together)

Redis keys per group:
  media_group:{group_id}        LIST  — serialised MediaGroupItem JSON
  media_group:{group_id}:ttl    STRING (EXPIRE) — debounce sentinel
  media_group:{group_id}:lock   STRING (SETNX)  — flush-once guard

§ Requirements
  - Redis keyspace notifications must be enabled for expired events.
    Set `notify-keyspace-events Ex` in redis.conf or at runtime:
        await redis.config_set("notify-keyspace-events", "Ex")
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
# Telegram typically sends all album photos within ~300 ms on a good connection,
# but on slow or congested mobile connections the last photo can arrive up to
# 2 seconds after the first. 3 s gives a safe margin while keeping latency
# acceptable. Anything below 2 s risks flushing before all photos arrive,
# producing partial albums ("described 8 of 10").
_DEBOUNCE_TTL_SECONDS: int = 3

# Hard cap: flush immediately if the group reaches this size.
# Telegram's own limit is 10 media per album; we honour that.
_MAX_GROUP_SIZE: int = 10

# Lua script: atomically RPUSH item + EXPIRE debounce key + return list length.
# Using Lua keeps the operation atomic across multiple bot instances.
_LUA_ADD = """
local list_key  = KEYS[1]
local ttl_key   = KEYS[2]
local item_json = ARGV[1]
local ttl_secs  = tonumber(ARGV[2])
local msg_id    = ARGV[3]
local seen_key  = KEYS[3]

-- Deduplication: skip if this message_id was already added.
if redis.call("SISMEMBER", seen_key, msg_id) == 1 then
    return redis.call("LLEN", list_key)
end
redis.call("SADD", seen_key, msg_id)
redis.call("EXPIRE", seen_key, ttl_secs * 10)

-- Append item and reset debounce TTL.
redis.call("RPUSH", list_key, item_json)
redis.call("SET",   ttl_key, "1", "EX", ttl_secs)

return redis.call("LLEN", list_key)
"""

# Lua script: atomically grab the list + delete it (flush-once).
#
# Lock lifecycle (ChatGPT review, май 2026):
#   The lock must be deleted in the SAME atomic script that acquires it,
#   immediately after collecting the data. Keeping the lock alive after
#   flush (even with a short TTL) blocks any second album the same user
#   sends within that window — producing the "ghost of previous album" bug.
#
#   Safe against double-processing: SETNX still guarantees only one worker
#   enters the critical section. Once data is collected and all keys are
#   deleted, a concurrent worker that lost the SETNX race gets nil → bails.
#   A new album that arrives after DEL starts with a clean slate.
_LUA_FLUSH = """
local list_key = KEYS[1]
local lock_key = KEYS[2]
local ttl_key  = KEYS[3]
local seen_key = KEYS[4]

-- Acquire flush lock (SETNX).  Returns 0 if already locked (another instance
-- is processing this group) → caller should discard.
if redis.call("SETNX", lock_key, "1") == 0 then
    return nil
end

-- Collect data and delete ALL keys including the lock atomically.
-- The lock must not outlive the flush: a subsequent album from the same
-- user must get a clean slate immediately, not after a 30-second TTL.
local items = redis.call("LRANGE", list_key, 0, -1)
redis.call("DEL", list_key, lock_key, ttl_key, seen_key)

return items
"""


@dataclass(frozen=True)
class MediaGroupItem:
    """One photo in an album."""
    file_id: str
    message_id: int
    caption: str = ""
    lang: str = "ru"  # detected language of the user's message / caption
    # The Worker already downloaded this photo into Supabase Storage and
    # attached {bucket, path, mime_type, size, kind} as `_attachment` on the
    # Telegram update (see ceyona-worker/worker.js::downloadAndStoreAttachment,
    # infra/attachment.py::from_pending_update_ref). Threading it through here
    # means handle_vision_group() can build an Attachment and read
    # attachment.bytes() straight from Storage — same target path as the
    # single-photo flow — instead of re-downloading via the Worker's /tg/
    # proxy per image. None if the Worker's own download/upload failed for
    # this specific update; the caller falls back to a per-image Telegram
    # re-download only for that one item, not the whole album.
    attachment_ref: dict | None = None


CallbackType = Callable[[str, list[MediaGroupItem]], Awaitable[None]]


class MediaGroupAggregator:
    """
    Redis-backed aggregator for Telegram media groups.

    Usage:
        aggregator = MediaGroupAggregator(redis_client, on_group_ready)
        await aggregator.start()          # subscribe to keyspace events
        ...
        await aggregator.add(group_id, item)
        ...
        await aggregator.stop()
    """

    def __init__(
        self,
        redis,                          # redis.asyncio.Redis — regular commands (add/flush)
        on_group_ready: CallbackType,
        debounce_ttl: int = _DEBOUNCE_TTL_SECONDS,
        max_group_size: int = _MAX_GROUP_SIZE,
        redis_pubsub=None,              # redis.asyncio.Redis — keyspace listener only.
                                         # Should be a client with socket_timeout=None
                                         # (pubsub.listen() blocks indefinitely between
                                         # events, which is normal idle, not a hang).
                                         # Falls back to `redis` if not given — that
                                         # client must then ALSO have socket_timeout=None,
                                         # which is correct for the ephemeral fallback
                                         # path in update_handler.py but would be wrong
                                         # for a client also used for regular GET/SETEX.
    ) -> None:
        self._redis = redis
        if redis_pubsub is None:
            logger.warning(
                "MediaGroupAggregator: no redis_pubsub given — reusing main "
                "redis client for the keyspace listener too. Fine for the "
                "ephemeral fallback path; if this is the app-level instance, "
                "bootstrap.py should be passing a dedicated socket_timeout=None client."
            )
            redis_pubsub = redis
        self._redis_pubsub = redis_pubsub
        self._on_group_ready = on_group_ready
        self._debounce_ttl = debounce_ttl
        self._max_group_size = max_group_size
        self._lua_add: object | None = None
        self._lua_flush: object | None = None
        self._listener_task: asyncio.Task | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Register Lua scripts and start the keyspace event listener."""
        self._lua_add   = self._redis.register_script(_LUA_ADD)
        self._lua_flush = self._redis.register_script(_LUA_FLUSH)

        # Enable keyspace notifications for expired events (idempotent).
        try:
            await self._redis.config_set("notify-keyspace-events", "Ex")
        except Exception as exc:
            logger.warning(
                "Could not set notify-keyspace-events — "
                "ensure Redis is configured with 'notify-keyspace-events Ex'",
                extra={"error": str(exc)},
            )

        self._listener_task = asyncio.create_task(
            self._keyspace_listener_supervisor(), name="media_group_keyspace_listener"
        )
        logger.info("MediaGroupAggregator started")

    async def stop(self) -> None:
        """Cancel the keyspace listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("MediaGroupAggregator stopped")

    # ── public API ────────────────────────────────────────────────────────────

    async def add(self, group_id: str, item: MediaGroupItem) -> None:
        """
        Add one photo to the group buffer.
        Flushes immediately if the group hits _max_group_size.
        """
        list_key  = f"media_group:{group_id}"
        ttl_key   = f"media_group:{group_id}:ttl"
        seen_key  = f"media_group:{group_id}:seen"

        length = await self._lua_add(
            keys=[list_key, ttl_key, seen_key],
            args=[
                json.dumps({
                    "file_id":        item.file_id,
                    "message_id":     item.message_id,
                    "caption":        item.caption,
                    "lang":           item.lang,
                    "attachment_ref": item.attachment_ref,
                }),
                str(self._debounce_ttl),
                str(item.message_id),
            ],
        )

        logger.debug(
            "MediaGroup item added",
            extra={"group_id": group_id, "length": length, "file_id": item.file_id[:20]},
        )

        # Immediate flush on max size (don't wait for TTL expiry).
        if length and int(length) >= self._max_group_size:
            logger.info(
                "MediaGroup hit max size — flushing immediately",
                extra={"group_id": group_id, "size": length},
            )
            await self._flush(group_id)

    # ── internals ─────────────────────────────────────────────────────────────

    async def _keyspace_listener_supervisor(self) -> None:
        """
        Restart _keyspace_listener on failure instead of letting one
        transient Redis hiccup permanently disable media-group flushing.
        Backs off briefly between restarts to avoid a hot-crash loop.
        """
        backoff = 1.0
        while True:
            try:
                await self._keyspace_listener()
                return  # clean exit (cancellation) — don't restart
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error(
                    "MediaGroupAggregator keyspace listener crashed — restarting",
                    extra={"error": str(exc)},
                    exc_info=True,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _keyspace_listener(self) -> None:
        """
        Subscribe to Redis keyspace expiry events.
        Fires _flush() when a debounce TTL key expires.

        Pattern: __keyevent@*__:expired  for keys matching media_group:*:ttl
        """
        pubsub = self._redis_pubsub.pubsub()
        # Subscribe to all DB keyevent channels for expired events.
        await pubsub.psubscribe("__keyevent@*__:expired")
        logger.debug("MediaGroupAggregator: subscribed to keyspace expiry events")

        try:
            async for message in pubsub.listen():
                if message["type"] not in ("pmessage", "message"):
                    continue
                key = message.get("data", b"")
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="replace")

                # We only care about our debounce sentinel keys.
                if not key.startswith("media_group:") or not key.endswith(":ttl"):
                    continue

                # Extract group_id from key: media_group:{group_id}:ttl
                group_id = key[len("media_group:"):-len(":ttl")]
                logger.debug(
                    "MediaGroup TTL expired — flushing",
                    extra={"group_id": group_id},
                )
                # Fire-and-forget: don't let one group's failure block others.
                asyncio.create_task(
                    self._flush(group_id),
                    name=f"media_group_flush_{group_id}",
                )
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.close()

    async def _flush(self, group_id: str) -> None:
        """
        Atomically retrieve and delete the group from Redis, then call
        on_group_ready.  The Lua flush script ensures only one instance
        processes a given group (flush-once guarantee via SETNX lock).
        """
        list_key  = f"media_group:{group_id}"
        lock_key  = f"media_group:{group_id}:lock"
        ttl_key   = f"media_group:{group_id}:ttl"
        seen_key  = f"media_group:{group_id}:seen"

        raw_items = await self._lua_flush(
            keys=[list_key, lock_key, ttl_key, seen_key],
            args=[],
        )

        if not raw_items:
            # Another instance already flushed this group.
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
                    attachment_ref=data.get("attachment_ref"),
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