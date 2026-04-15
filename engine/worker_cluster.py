import asyncio


class WorkerCluster:
    """
    Simulates distributed AI execution nodes
    """

    def __init__(self, workers=3):
        self.workers = workers

    async def execute(self, tasks):
        async def run(task):
            return await task()

        return await asyncio.gather(*[run(t) for t in tasks])