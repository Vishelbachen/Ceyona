import asyncio


class TaskQueue:
    """
    Lightweight async job queue (Celery-like mini system)
    """

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
            self.queue.task_done()