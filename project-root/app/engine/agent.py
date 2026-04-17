class Agent:
    def __init__(self, planner, router, formatter, llm, memory):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm
        self.memory = memory

    async def run(self, text: str, user_id: str = None):

        # =========================
        # 1. MEMORY CONTEXT
        # =========================
        memory_context = ""
        if user_id:
            memory_context = await self.memory.get(user_id)

        # =========================
        # 2. PLAN
        # =========================
        intent = await self.planner.parse(text, memory_context)

        # =========================
        # 3. COST FILTER (NEW)
        # =========================
        if await self.is_expensive(intent):
            intent = await self.optimize_intent(intent)

        # =========================
        # 4. EXECUTION
        # =========================
        result = await self.router.execute(intent)

        # =========================
        # 5. SELF DEBUGGER (NEW)
        # =========================
        if await self.is_broken(result):
            debug_info = await self.debug(text, intent, result)
            intent = debug_info.get("fixed_intent", intent)
            result = await self.router.execute(intent)

        # =========================
        # 6. FORMAT RESPONSE
        # =========================
        response = await self.formatter.format(intent, result)

        # =========================
        # 7. SAVE MEMORY
        # =========================
        if user_id:
            await self.memory.save(user_id, text, response)

        return response

    # =========================
    # COST CONTROL
    # =========================
    async def is_expensive(self, intent):
        expensive_tools = ["multi_map_chain", "deep_search"]

        if intent.get("tool") in expensive_tools:
            return True

        if intent.get("steps") and len(intent["steps"]) > 2:
            return True

        return False

    async def optimize_intent(self, intent):
        # упрощение запроса
        intent["steps"] = intent.get("steps", [])[:2]
        return intent

    # =========================
    # FAILURE DETECTION
    # =========================
    async def is_broken(self, result):
        if not result:
            return True

        if isinstance(result, dict) and "error" in result:
            return True

        return False

    # =========================
    # SELF DEBUGGER
    # =========================
    async def debug(self, text, intent, result):

        prompt = f"""
Find problem in execution.

User:
{text}

Intent:
{intent}

Result:
{result}

Return JSON:
{{
  "fixed_intent": {{
    "tool": "...",
    "query": "..."
  }}
}}
"""

        try:
            res = await self.llm(prompt)
            return eval(res) if isinstance(res, str) else res
        except:
            return {"fixed_intent": intent}