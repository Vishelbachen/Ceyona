class BackgroundWorker:
    def __init__(self, memory, router):
        self.memory = memory
        self.router = router

    async def run(self, event: dict):

        if event.get("type") == "user_interaction":
            await self.memory.store(event["user_id"], event["text"])

        if event.get("type") == "tool_failure":
            await self.router.retry(event["payload"])