import asyncio


class TaskQueue:
    def __init__(self):
        self.q = asyncio.Queue()

    async def add(self, task):
        await self.q.put(task)

    async def worker(self):
        while True:
            task = await self.q.get()
            try:
                await task()
            except Exception:
                pass
            self.q.task_done()