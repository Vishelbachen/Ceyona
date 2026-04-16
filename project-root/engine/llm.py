import os
from groq import Groq
from google import genai


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.gemini_client = None

        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)

    async def generate(self, text: str) -> str:
        groq_answer = None
        gemini_answer = None

        # ===== GROQ =====
        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        # ===== GEMINI =====
        if self.gemini_client:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        # ===== FALLBACKS =====
        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        if not groq_answer and not gemini_answer:
            return "❌ No models available"

        # ===== SIMPLE DECISION =====
        if len(groq_answer) >= len(gemini_answer):
            return f"🔥 FINAL (GROQ):\n{groq_answer}"
        else:
            return f"🔥 FINAL (GEMINI):\n{gemini_answer}"

    # =========================
    # GROQ
    # =========================

    async def _groq(self, text: str) -> str:
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    # =========================
    # GEMINI
    # =========================

    async def _gemini(self, text: str) -> str:
        response = self.gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=text
        )
        return response.text