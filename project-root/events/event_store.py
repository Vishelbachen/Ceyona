import json
import logging
from datetime import timezone

from events.event_types import BaseEvent
from infra import redis_keys
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "events"
_KEY_ALL = f"{_KEY_PREFIX}:all"
_KEY_USER = f"{_KEY_PREFIX}:user"
_TTL_SECONDS = 60 * 60 * 24 * 30   # 30 days


def _serialize(event: BaseEvent) -> str:
    return json.dumps({
        "event_id":  event.event_id,
        "name":      event.name,
        "user_id":   event.user_id,
        "payload":   event.payload,
        "timestamp": event.timestamp.isoformat(),
    })


class EventStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def append(self, event: BaseEvent) -> None:
        """
        Append event to the global stream and user-specific stream.
        Fire-and-forget safe — errors are logged, never raised.
        """
        try:
            score = event.timestamp.replace(tzinfo=timezone.utc).timestamp()
            data = _serialize(event)

            pipe = self._redis.pipeline()

            # global stream
            pipe.zadd(_KEY_ALL, {data: score})
            pipe.expire(_KEY_ALL, _TTL_SECONDS)

            # per-user stream
            if event.user_id is not None:
                user_key = f"{_KEY_USER}:{event.user_id}"
                pipe.zadd(user_key, {data: score})
                pipe.expire(user_key, _TTL_SECONDS)

            await pipe.execute()

        except Exception as exc:
            logger.warning(
                "EventStore.append failed",
                extra={"event": event.name, "error": str(exc)},
            )

    async def read_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Read latest events from global stream. Used by event_replay only."""
        try:
            raw = await self._redis.zrevrange(
                _KEY_ALL, offset, offset + limit - 1
            )
            return [json.loads(r) for r in raw]
        except Exception as exc:
            logger.warning("EventStore.read_all failed", extra={"error": str(exc)})
            return []

    async def read_user(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[dict]:
        """Read latest events for a specific user. Used by event_replay only."""
        try:
            user_key = f"{_KEY_USER}:{user_id}"
            raw = await self._redis.zrevrange(user_key, 0, limit - 1)
            return [json.loads(r) for r in raw]
        except Exception as exc:
            logger.warning("EventStore.read_user failed", extra={"error": str(exc)})
            return []

    async def clear_low_balance_warning(self, user_id: int) -> None:
        """
        Reset the 24 h dedup flag after a successful top-up.
        Called by event_dispatcher on BALANCE_CREDITED.
        Dispatcher knows nothing about Redis or key formats.
        """
        try:
            await self._redis.delete(redis_keys.low_balance_warning(user_id))
        except Exception as exc:
            logger.warning(
                "EventStore.clear_low_balance_warning failed",
                extra={"user_id": user_id, "error": str(exc)},
            )