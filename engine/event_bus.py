import asyncio
from collections import defaultdict


class EventBus:
    """
    Internal AI event system (OpenAI-style orchestration backbone)
    """

    def __init__(self):
        self.listeners = defaultdict(list)

    def subscribe(self, event: str, handler):
        self.listeners[event].append(handler)

    async def emit(self, event: str, payload: dict):
        if event not in self.listeners:
            return

        tasks = [
            handler(payload)
            for handler in self.listeners[event]
        ]

        await asyncio.gather(*tasks, return_exceptions=True)