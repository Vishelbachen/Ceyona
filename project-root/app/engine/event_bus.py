class EventBus:
    def __init__(self):
        self.subscribers = {}

    async def emit(self, event_type: str, data: dict):
        if event_type not in self.subscribers:
            return

        for handler in self.subscribers[event_type]:
            await handler(data)

    def subscribe(self, event_type: str, handler):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)