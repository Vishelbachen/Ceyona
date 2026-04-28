from typing import Any, Callable, Dict, List
from collections import defaultdict
import asyncio


class EventBus:
    """
    AI Platform v4.7 — Event Bus

    RESPONSIBILITY:
    - Internal pub/sub event dispatching
    - Decoupling system components
    - Async event propagation

    STRICT RULES:
    - No business logic
    - No decision-making
    - No LLM / retrieval / memory access
    - No orchestration control
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """
        Register event handler.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, event: Dict[str, Any]) -> None:
        """
        Emit event to all subscribers (async-safe).
        """

        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            result = handler(event)

            # allow async handlers
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

    async def publish_async(self, event_type: str, event: Dict[str, Any]) -> None:
        """
        Fully async event dispatch.
        """

        handlers = self._subscribers.get(event_type, [])

        tasks = []

        for handler in handlers:
            result = handler(event)

            if asyncio.iscoroutine(result):
                tasks.append(result)

        if tasks:
            await asyncio.gather(*tasks)