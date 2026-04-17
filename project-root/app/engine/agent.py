import json


class Agent:
    def __init__(self, planner, router, formatter, llm, memory, event_bus=None):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm
        self.memory = memory
        self.event_bus = event_bus

    # =========================
    # MAIN ENTRY
    # =========================
    async def run(self, text: str, user_id: str = None):

        # =========================
        # EVENT: USER INPUT (V6)
        # =========================
        if self.event_bus:
            try:
                await self.event_bus.emit("user_message", {
                    "user_id": user_id,
                    "text": text
                })
            except:
                pass

        # =========================
        # MEMORY CONTEXT
        # =========================
        memory_context = ""
        if user_id:
            try:
                memory_context = await self.memory.get(user_id)
            except:
                memory_context = ""

        # =========================
        # PLAN
        # =========================
        intent = await self.planner.parse(text, memory_context)

        # STRICT VALIDATION (V6)
        if not self._is_valid_intent(intent):
            return await self.llm(text)

        # =========================
        # COST CONTROL
        # =========================
        if await self.is_expensive(intent):
            intent = await self.optimize_intent(intent)

        # =========================
        # EXECUTION
        # =========================
        result = await self.router.execute(intent)

        # =========================
        # EVENT: TOOL FAILURE (V6)
        # =========================
        if self.event_bus and self.is_broken(result):
            try:
                await self.event_bus.emit("tool_failure", {
                    "intent": intent,
                    "result": result
                })
            except:
                pass

        # =========================
        # SELF HEALING
        # =========================
        if await self.is_broken(result):
            fixed_intent = await self.debug(text, intent, result)

            if self._is_valid_intent(fixed_intent):
                intent = fixed_intent
                result = await self.router.execute(intent)

        # =========================
        # FORMAT RESPONSE
        # =========================
        response = await self.formatter.format(intent, result)

        # =========================
        # MEMORY SAVE (ASYNC SAFE)
        # =========================
        if user_id:
            try:
                await self.memory.save(user_id, text, response)
            except:
                pass

        return response

    # =========================
    # INTENT VALIDATION (V6)
    # =========================
    def _is_valid_intent(self, intent):
        if not isinstance(intent, dict):
            return False

        if "tool" not in intent and "steps" not in intent:
            return False

        return True

    # =========================
    # COST CONTROL
    # =========================
    async def is_expensive(self, intent):
        expensive_tools = ["multi_map_chain", "deep_search"]

        if intent.get("tool") in expensive_tools:
            return True

        steps = intent.get("steps", [])
        if isinstance(steps, list) and len(steps) > 2:
            return True

        return False

    async def optimize_intent(self, intent):
        if "steps" in intent and isinstance(intent["steps"], list):
            intent["steps"] = intent["steps"][:2]

        return intent

    # =========================
    # FAILURE DETECTION
    # =========================
    def is_broken(self, result):
        if result is None:
            return True

        if isinstance(result, dict) and "error" in result:
            return True

        return False

    # =========================
    # SELF DEBUGGER (SAFE)
    # =========================
    async def debug(self, text, intent, result):

        prompt = f"""
Fix failed execution intent.

User:
{text}

Intent:
{json.dumps(intent, ensure_ascii=False)}

Result:
{json.dumps(result, ensure_ascii=False)}

Return ONLY JSON:
{{
  "tool": "...",
  "query": "..."
}}
"""

        try:
            raw = await self.llm(prompt)

            if not raw:
                return None

            if isinstance(raw, dict):
                return raw

            return json.loads(raw)

        except:
            return None