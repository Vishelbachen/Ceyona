class Scheduler:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def schedule(self, event_type: str, data: dict, delay: int):
        import asyncio

        await asyncio.sleep(delay)
        await self.event_bus.emit(event_type, data)