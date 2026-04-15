import asyncio


class BackgroundWorkers:
    """
    Runs autonomous background AI tasks (non-blocking)
    """

    def __init__(self):
        self.queue = []

    def add_task(self, task):
        self.queue.append(task)

    async def run(self):
        while True:
            if self.queue:
                task = self.queue.pop(0)
                try:
                    await task()
                except:
                    pass

            await asyncio.sleep(1)