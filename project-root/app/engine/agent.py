class Agent:
    def __init__(self, planner, router, formatter, llm, memory):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm
        self.memory = memory

    async def run(self, text: str, user_id: str = None):

        # =========================
        # 0. MEMORY CONTEXT (NEW)
        # =========================
        memory_context = ""
        if user_id:
            memory_context = await self.memory.get(user_id)

        # =========================
        # 1. PLAN (memory-aware)
        # =========================
        intent = await self.planner.parse(text, memory_context)

        if not intent or intent.get("tool") == "none":
            return await self.llm(text)

        # =========================
        # 2. MULTI-TOOL CHAINING (NEW)
        # =========================
        results = []

        for step in intent.get("steps", [intent]):
            tool_result = await self.router.execute(step)
            results.append(tool_result)

        # =========================
        # 3. MERGE RESULTS
        # =========================
        merged = await self.merge_results(results)

        # =========================
        # 4. REFLECTION (light v3)
        # =========================
        if await self.needs_refine(text, merged):
            intent = await self.planner.parse(text, memory_context)
            merged = await self.router.execute(intent)

        # =========================
        # 5. FORMAT RESPONSE
        # =========================
        response = await self.formatter.format(intent, merged)

        # =========================
        # 6. SAVE MEMORY (NEW)
        # =========================
        if user_id:
            await self.memory.save(user_id, text, response)

        return response

    # =========================
    # MERGE MULTI TOOL RESULTS
    # =========================
    async def merge_results(self, results):
        clean = []

        for r in results:
            if isinstance(r, dict) and "error" not in r:
                clean.append(r)

        return clean if clean else results

    # =========================
    # LIGHT REFLECTION (OPTIMIZED)
    # =========================
    async def needs_refine(self, text: str, result):

        prompt = f"""
Check if result is sufficient.

User:
{text}

Result:
{result}

Return:
true or false only
"""

        try:
            res = await self.llm(prompt)
            return "true" in str(res).lower()
        except:
            return False