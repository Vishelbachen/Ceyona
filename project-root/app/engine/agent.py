import json


class Agent:
    def __init__(self, planner, router, formatter, llm, memory, event_bus=None):
        self.planner = planner
        self.router = router
        self.formatter = formatter
        self.llm = llm
        self.memory = memory
        self.event_bus = event_bus

    async def run(self, text: str, user_id: str = None):

        if self.event_bus:
            try:
                await self.event_bus.emit("user_message", {
                    "user_id": user_id,
                    "text": text
                })
            except Exception:
                pass

        memory_context = ""
        if user_id:
            try:
                memory_context = await self.memory.get(user_id)
            except Exception:
                memory_context = ""

        intent = await self.planner.parse(text, memory_context)

        if not self._is_valid_intent(intent):
            fallback = {"tool": "llm", "query": text}
            result = await self.router.execute(fallback)
            return await self.formatter.format(fallback, result)

        if await self.is_expensive(intent):
            intent = await self.optimize_intent(intent)

        result = await self.router.execute(intent)

        if self.event_bus and self.is_broken(result):
            try:
                await self.event_bus.emit("tool_failure", {
                    "intent": intent,
                    "result": result
                })
            except Exception:
                pass

        if self.is_broken(result):
            fixed = await self.debug(text, intent, result)

            if fixed and self._is_valid_intent(fixed):
                intent = fixed
                result = await self.router.execute(intent)

        response = await self.formatter.format(intent, result)

        if user_id:
            try:
                await self.memory.save(user_id, text, response)
            except Exception:
                pass

        return response

    def _is_valid_intent(self, intent):
        return isinstance(intent, dict) and ("tool" in intent or "steps" in intent)

    async def is_expensive(self, intent):
        if not intent:
            return False

        if intent.get("tool") in ["multi_map_chain", "deep_search"]:
            return True

        steps = intent.get("steps", [])
        return isinstance(steps, list) and len(steps) > 2

    async def optimize_intent(self, intent):
        if isinstance(intent.get("steps"), list):
            intent["steps"] = intent["steps"][:2]
        return intent

    def is_broken(self, result):
        if result is None:
            return True
        if isinstance(result, dict) and "error" in result:
            return True
        return False

    async def debug(self, text, intent, result):
        prompt = {
            "user": text,
            "intent": intent,
            "result": result,
            "output_format": "json"
        }

        try:
            raw = await self.llm(json.dumps(prompt))

            if isinstance(raw, dict):
                return raw

            return json.loads(raw)

        except Exception:
            return None