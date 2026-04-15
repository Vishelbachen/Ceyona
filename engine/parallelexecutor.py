import asyncio


class ParallelExecutor:
    """
    Executes multiple tasks simultaneously (true async AI behavior)
    """

    async def run(self, tasks):
        return await asyncio.gather(*tasks)