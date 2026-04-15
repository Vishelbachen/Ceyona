import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event: str, handler):
        self.listeners[event].append(handler)

    async def emit(self, event: str, data: dict):
        tasks = [
            handler(data)
            for handler in self.listeners[event]
        ]
        await asyncio.gather(*tasks, return_exceptions=True)