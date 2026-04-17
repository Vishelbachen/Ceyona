import asyncio


class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def add(self, task):
        await self.queue.put(task)

    async def worker(self):
        while True:
            task = await self.queue.get()
            try:
                await task()
            except Exception:
                pass
            finally:
                self.queue.task_done()