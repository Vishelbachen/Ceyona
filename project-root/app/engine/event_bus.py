import asyncio


class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, handler):
        self.subscribers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, data: dict):
        handlers = self.subscribers.get(event_type, [])
        await asyncio.gather(*(self._safe_call(h, data) for h in handlers))

    async def _safe_call(self, handler, data):
        try:
            await handler(data)
        except Exception:
            pass