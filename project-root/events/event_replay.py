import logging
from typing import Awaitable, Callable

from events.event_store import EventStore
from events.event_types import EventName

logger = logging.getLogger(__name__)

ReplayHandler = Callable[[dict], Awaitable[None]]


class EventReplay:
    def __init__(self, store: EventStore) -> None:
        self._store = store

    async def replay_all(
        self,
        handler: ReplayHandler,
        limit: int = 100,
    ) -> int:
        """
        Replay global event stream to handler.
        Returns number of events replayed.
        """
        events = await self._store.read_all(limit=limit)
        for event in events:
            await self._safe_call(handler, event)
        logger.info("Replay complete", extra={"count": len(events)})
        return len(events)

    async def replay_user(
        self,
        user_id: int,
        handler: ReplayHandler,
        limit: int = 50,
    ) -> int:
        """
        Replay event stream for a specific user.
        Returns number of events replayed.
        """
        events = await self._store.read_user(user_id=user_id, limit=limit)
        for event in events:
            await self._safe_call(handler, event)
        logger.info(
            "User replay complete",
            extra={"user_id": user_id, "count": len(events)},
        )
        return len(events)

    async def replay_by_name(
        self,
        user_id: int,
        event_name: EventName,
        handler: ReplayHandler,
        limit: int = 50,
    ) -> int:
        """
        Replay only events matching a specific name for a user.
        Filtering is done in-process (store has no query capability by design).
        """
        events = await self._store.read_user(user_id=user_id, limit=limit)
        filtered = [e for e in events if e.get("name") == event_name]
        for event in filtered:
            await self._safe_call(handler, event)
        return len(filtered)

    @staticmethod
    async def _safe_call(handler: ReplayHandler, event: dict) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.warning(
                "Replay handler failed",
                extra={"event": event.get("name"), "error": str(exc)},
            )