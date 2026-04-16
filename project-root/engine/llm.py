import os
from groq import Groq
import google.generativeai as genai


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        print("🔍 GROQ:", "OK" if self.groq_key else "MISSING")
        print("🔍 GEMINI:", "OK" if self.gemini_key else "MISSING")

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    async def generate(self, text: str) -> str:
        # ===== TRY GROQ FIRST =====
        if self.groq_key:
            try:
                response = await self._groq(text)
                return f"🧠 GROQ:\n{response}"
            except Exception as e:
                print("❌ Groq failed:", e)

        # ===== FALLBACK GEMINI =====
        if self.gemini_key:
            try:
                response = await self._gemini(text)
                return f"✨ GEMINI:\n{response}"
            except Exception as e:
                print("❌ Gemini failed:", e)

        return "❌ Нет доступных моделей"

    async def _groq(self, text: str) -> str:
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a smart, helpful AI assistant. Answer clearly."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return res.choices[0].message.content

    async def _gemini(self, text: str) -> str:
        model = genai.GenerativeModel("gemini-pro")
        res = model.generate_content(text)

        return res.text if res.text else "⚠️ Gemini пустой ответ"