class Agent:
    def __init__(self, planner, router, formatter, llm, memory, event_bus):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm
        self.memory = memory
        self.event_bus = event_bus

    async def run(self, text: str, user_id: str = None):

        # =========================
        # EMIT EVENT (NEW)
        # =========================
        await self.event_bus.emit("user_interaction", {
            "user_id": user_id,
            "text": text
        })

        # =========================
        # MEMORY
        # =========================
        memory_context = ""
        if user_id:
            memory_context = await self.memory.get(user_id)

        # =========================
        # PLAN
        # =========================
        intent = await self.planner.parse(text, memory_context)

        # =========================
        # EXECUTE
        # =========================
        result = await self.router.execute(intent)

        # =========================
        # FAILURE EVENT
        # =========================
        if not result or "error" in str(result):
            await self.event_bus.emit("tool_failure", {
                "intent": intent,
                "result": result
            })

        # =========================
        # FORMAT
        # =========================
        response = await self.formatter.format(intent, result)

        # =========================
        # MEMORY SAVE
        # =========================
        if user_id:
            await self.memory.save(user_id, text, response)

        return response