class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, handler):
        self.subscribers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, data: dict):
        handlers = self.subscribers.get(event_type, [])
        for h in handlers:
            try:
                await h(data)
            except:
                pass