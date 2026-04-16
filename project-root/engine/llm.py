import os
from groq import Groq
import google.generativeai as genai


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    async def generate(self, text: str) -> str:
        groq_answer = None
        gemini_answer = None

        # ===== AGENT 1: GROQ =====
        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        # ===== AGENT 2: GEMINI =====
        if self.gemini_key:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        if not groq_answer and not gemini_answer:
            return "❌ No models available"

        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        # ===== JUDGE (логика без AI зависимости) =====
        best = self._judge_logic(groq_answer, gemini_answer)

        # ===== FIXER (ОТДЕЛЬНЫЙ ПРОХОД) =====
        fixed = await self._fix(text, best)

        return f"🔥 FINAL:\n{fixed}"

    # =========================
    # MODELS
    # =========================

    async def _groq(self, text: str) -> str:
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    async def _gemini(self, text: str) -> str:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(text)
        return res.text

    # =========================
    # JUDGE (НЕ ИИ, А ПРАВИЛА)
    # =========================

    def _judge_logic(self, a1, a2):
        # простая эвристика (очень важно!)
        if len(a2) > len(a1):
            return a2
        return a1

    # =========================
    # FIXER (Gemini как редактор)
    # =========================

    async def _fix(self, question, answer):
        prompt = f"""
Improve and correct the answer if needed.

Question:
{question}

Answer:
{answer}

Return only final corrected answer.
"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)

        return res.text