class Agent:
    def __init__(self, planner, router, formatter, llm):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm

    async def run(self, text: str, memory: str = ""):

        # =========================
        # 1. PLAN
        # =========================
        intent = await self.planner.parse(text)

        if not intent or intent.get("tool") == "none":
            return await self.llm(text)

        # =========================
        # 2. EXECUTE
        # =========================
        tool_result = await self.router.execute(intent)

        # =========================
        # 3. REFLECTION (NEW)
        # =========================
        reflection = await self.reflect(text, intent, tool_result)

        # если агент решил что ответ плохой → fallback
        if reflection.get("retry"):
            intent = reflection.get("new_intent", intent)
            tool_result = await self.router.execute(intent)

        # =========================
        # 4. FORMAT
        # =========================
        return await self.formatter.format(intent, tool_result)

    # =========================
    # SELF-REFLECTION LAYER
    # =========================
    async def reflect(self, text: str, intent: dict, tool_result: dict):

        prompt = f"""
Evaluate the response quality.

User input:
{text}

Intent:
{intent}

Tool result:
{tool_result}

Return JSON ONLY:
{
  "retry": true/false,
  "reason": "short reason",
  "new_intent": {{"tool": "...", "query": "..."}}
}

Rules:
- If tool_result is empty or error → retry = true
- If data is sufficient → retry = false
"""

        try:
            res = await self.llm(prompt)
            return eval(res) if isinstance(res, str) else res
        except:
            return {"retry": False}