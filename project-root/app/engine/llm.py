import os
from groq import Groq

from engine.memory.service import build_memory_context
from engine.memory.project_memory import get_project_memory
from engine.tool_router import ToolRouter


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.tools = ToolRouter()

        self.client = Groq(api_key=self.groq_key) if self.groq_key else None

    def _build_context(self, user_id: str, text: str) -> str:
        try:
            user_memory = build_memory_context(user_id)
        except:
            user_memory = ""

        try:
            project_memory = get_project_memory()
        except:
            project_memory = []

        pm_text = "\n".join([str(x) for x in project_memory if x])

        return f"""
[PROJECT MEMORY]
{pm_text}

[USER MEMORY]
{user_memory}

[USER MESSAGE]
{text}
"""

    async def generate(self, text: str, user_id: str = None):

        tool_result = None
        try:
            tool_result = await self.tools.route(text)
        except:
            tool_result = None

        if tool_result:
            return f"{tool_result}"

        if user_id:
            text = self._build_context(user_id, text)

        if not self.client:
            return "LLM not available"

        return await self._groq(text)

    async def _groq(self, text: str):
        res = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": text}
            ]
        )

        return res.choices[0].message.content