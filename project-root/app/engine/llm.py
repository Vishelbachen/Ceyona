import os
from groq import Groq
import google.generativeai as genai

from engine.memory.service import build_memory_context
from engine.memory.project_memory import get_project_memory
from engine.tool_router import ToolRouter


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.tools = None
        try:
            self.tools = ToolRouter()
        except Exception as e:
            print("ToolRouter disabled:", e)

        self.gemini_model = None

        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                print("Gemini disabled:", e)

    def _build_context(self, user_id: str, text: str) -> str:
        try:
            user_memory = build_memory_context(user_id)
        except:
            user_memory = ""

        try:
            project_memory = get_project_memory()
        except:
            project_memory = []

        return f"""
[PROJECT]
{project_memory}

[USER]
{user_memory}

[INPUT]
{text}
"""

    async def generate(self, text: str, user_id: str = None):

        # TOOL FIRST (SAFE)
        if self.tools:
            try:
                tool = await self.tools.route(text)
                if tool:
                    return f"🛠 {tool}"
            except:
                pass

        # CONTEXT
        if user_id:
            try:
                text = self._build_context(user_id, text)
            except:
                pass

        groq_answer = None
        gemini_answer = None

        # GROQ
        try:
            if self.groq_key:
                groq_answer = await self._groq(text)
        except:
            pass

        # GEMINI
        try:
            if self.gemini_model:
                gemini_answer = await self._gemini(text)
        except:
            pass

        # FALLBACK
        if groq_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        return "❌ No models available"

    async def _groq(self, text):
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    async def _gemini(self, text):
        return self.gemini_model.generate_content(text).text