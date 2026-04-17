import asyncio


class Scheduler:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def schedule(self, event_type: str, data: dict, delay: int):
        asyncio.create_task(self._run(event_type, data, delay))

    async def _run(self, event_type: str, data: dict, delay: int):
        await asyncio.sleep(delay)
        await self.event_bus.emit(event_type, data)