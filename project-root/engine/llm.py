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

        self.tools = ToolRouter()

        # =========================
        # GEMINI STABLE INIT
        # =========================
        self.gemini_model = None

        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)

                # сразу создаём модель (без v1beta клиента)
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")

            except Exception as e:
                print("Gemini init failed:", e)
                self.gemini_model = None

    # =========================
    # CONTEXT BUILDER (SAFE)
    # =========================
    def _build_context(self, user_id: str, text: str) -> str:
        try:
            user_memory = build_memory_context(user_id)
        except Exception as e:
            print("User memory error:", e)
            user_memory = ""

        try:
            project_memory = get_project_memory()
        except Exception as e:
            print("Project memory error:", e)
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

    # =========================
    # MAIN PIPELINE
    # =========================
    async def generate(self, text: str, user_id: str = None):

        # =========================
        # 1. TOOL LAYER (FIRST)
        # =========================
        try:
            tool_result = await self.tools.route(text)
            if tool_result:
                return f"🛠 TOOL RESULT:\n{tool_result}"
        except Exception as e:
            print("Tool error:", e)

        # =========================
        # 2. CONTEXT
        # =========================
        if user_id:
            try:
                text = self._build_context(user_id, text)
            except Exception as e:
                print("Context build error:", e)

        groq_answer = None
        gemini_answer = None

        # =========================
        # 3. GROQ
        # =========================
        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        # =========================
        # 4. GEMINI (SAFE)
        # =========================
        if self.gemini_model:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        # =========================
        # 5. FALLBACKS
        # =========================
        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        if not groq_answer and not gemini_answer:
            return "❌ No models available"

        # =========================
        # 6. DECISION
        # =========================
        if len(str(groq_answer)) >= len(str(gemini_answer)):
            return f"🔥 FINAL (GROQ):\n{groq_answer}"

        return f"🔥 FINAL (GEMINI):\n{gemini_answer}"

    # =========================
    # GROQ
    # =========================
    async def _groq(self, text: str):
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    # =========================
    # GEMINI (STABLE + NO 404 CRASH)
    # =========================
    async def _gemini(self, text: str):
        try:
            return self.gemini_model.generate_content(text).text
        except Exception as e:
            print("Gemini runtime error:", e)
            return None