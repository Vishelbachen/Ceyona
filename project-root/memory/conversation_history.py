import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "conv"
_MAX_TURNS = 20          # keep last 20 messages per user
_TTL_SECONDS = 60 * 60 * 24 * 7   # 7 days


class ConversationHistory:
    """
    Redis-backed sliding window of conversation turns per user.
    Storage only. No semantic logic. No summarization.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, user_id: int) -> str:
        return f"{_KEY_PREFIX}:{user_id}"

    async def append(self, user_id: int, role: str, content: str) -> None:
        """
        Append a single message turn.
        role: 'user' | 'assistant'
        Trims to _MAX_TURNS automatically.
        """
        key = self._key(user_id)
        message = json.dumps({"role": role, "content": content})
        try:
            pipe = self._redis.pipeline()
            pipe.rpush(key, message)
            pipe.ltrim(key, -_MAX_TURNS, -1)
            pipe.expire(key, _TTL_SECONDS)
            await pipe.execute()
        except Exception as exc:
            logger.warning("ConversationHistory.append failed", extra={
                "user_id": user_id, "error": str(exc)
            })

    async def get(self, user_id: int) -> list[dict]:
        """
        Return conversation history as list of {role, content} dicts.
        Ready to pass directly into build_messages().
        """
        key = self._key(user_id)
        try:
            raw = await self._redis.lrange(key, 0, -1)
            return [json.loads(m) for m in raw]
        except Exception as exc:
            logger.warning("ConversationHistory.get failed", extra={
                "user_id": user_id, "error": str(exc)
            })
            return []

    async def clear(self, user_id: int) -> None:
        """Delete full history for a user."""
        try:
            await self._redis.delete(self._key(user_id))
        except Exception as exc:
            logger.warning("ConversationHistory.clear failed", extra={
                "user_id": user_id, "error": str(exc)
            })