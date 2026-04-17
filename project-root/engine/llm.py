import os
from groq import Groq
from google import genai

from engine.memory.service import build_memory_context
from engine.memory.project_memory import get_project_memory


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.gemini_client = None
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)

    def _build_context(self, user_id: str, text: str) -> str:
        user_memory = build_memory_context(user_id)
        project_memory = get_project_memory()

        pm_text = "\n".join([str(x) for x in project_memory])

        return f"""
[PROJECT MEMORY]
{pm_text}

[USER MEMORY]
{user_memory}

[USER MESSAGE]
{text}
"""

    async def generate(self, text: str, user_id: str = None):

        if user_id:
            text = self._build_context(user_id, text)

        groq_answer = None
        gemini_answer = None

        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        if self.gemini_client:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        if not groq_answer and not gemini_answer:
            return "❌ No models available"

        return f"🔥 GROQ:\n{groq_answer}"

    async def _groq(self, text: str):
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    async def _gemini(self, text: str):
        res = self.gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=text
        )
        return res.text