import json


class Agent:
    def __init__(self, llm, memory, tool_router=None):
        self.llm = llm
        self.memory = memory
        self.tool_router = tool_router

    async def run(self, user_id: str, text: str):

        history = await self.memory.get_history(user_id)
        context = self._build_context(history, text)

        intent = await self._plan(context)

        if not intent:
            return await self.llm(context)

        tool_result = None

        if self.tool_router and intent.get("tool"):
            tool_result = await self.tool_router.route(intent)

        response = await self._generate(context, intent, tool_result)

        await self.memory.save_message(user_id, "user", text)
        await self.memory.save_message(user_id, "assistant", response)

        return response

    def _build_context(self, history, text: str) -> str:
        messages = []

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append(f"{role}: {content}")

        messages.append(f"user: {text}")

        return "\n".join(messages)

    async def _plan(self, context: str):
        prompt = f"""
Return JSON only.

Decide best action.

Context:
{context}

Output format:
{{
  "tool": null or string,
  "query": string or null
}}
"""

        try:
            raw = await self.llm(prompt)

            if isinstance(raw, str):
                return json.loads(raw)

            return None

        except:
            return None

    async def _generate(self, context, intent, tool_result):

        prompt = f"""
You are an advanced assistant.

Context:
{context}

Intent:
{json.dumps(intent, ensure_ascii=False)}

Tool result:
{tool_result}

Respond naturally, multilingual allowed.
"""

        return await self.llm(prompt)