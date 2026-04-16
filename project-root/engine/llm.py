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

        # ===== GENERATION =====
        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        if self.gemini_key:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        # ===== SINGLE MODEL FALLBACK =====
        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        if not groq_answer and not gemini_answer:
            return "❌ Нет доступных моделей"

        # ===== JUDGE =====
        best = await self._judge(text, groq_answer, gemini_answer)

        # ===== FIXER =====
        fixed = await self._fix(text, best)

        return f"🧠 FINAL ANSWER:\n{fixed}"

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
        model = genai.GenerativeModel("gemini-pro")
        res = model.generate_content(text)
        return res.text

    # =========================
    # JUDGE
    # =========================

    async def _judge(self, question, a1, a2):
        prompt = f"""
Ты — строгий эксперт.

Вопрос:
{question}

Ответ 1:
{a1}

Ответ 2:
{a2}

Задача:
1. Найди ошибки
2. Выбери лучший ответ
3. Верни ТОЛЬКО лучший ответ (без объяснений)
"""

        return await self._gemini(prompt)

    # =========================
    # FIXER
    # =========================

    async def _fix(self, question, answer):
        prompt = f"""
Ты — AI, который исправляет ошибки.

Вопрос:
{question}

Ответ:
{answer}

Задача:
- исправь возможные ошибки
- сделай ответ точным
- не добавляй лишнего
"""

        return await self._gemini(prompt)