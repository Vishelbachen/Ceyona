class Agent:
    def __init__(self, planner, router, formatter):
        self.planner = planner
        self.router = router
        self.formatter = formatter

    async def run(self, text: str, user_id: str = None):

        # 1. PLAN
        intent = await self.planner.parse(text)

        if not intent or intent.get("tool") == "none":
            return text  # fallback to LLM later in pipeline

        # 2. EXECUTE TOOL
        tool_result = await self.router.execute(intent)

        # 3. FORMAT RESPONSE
        response = await self.formatter.format(intent, tool_result)

        return response