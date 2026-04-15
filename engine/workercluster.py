import asyncio


class WorkerCluster:
    def __init__(self, size=4):
        self.size = size

    async def run(self, tasks):
        return await asyncio.gather(*tasks)