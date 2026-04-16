import os
from groq import Groq
import google.generativeai as genai

from engine.verifier import Verifier


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

        self.verifier = Verifier()

    # =========================
    # MAIN PIPELINE
    # =========================

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

        # ===== JUDGE (REAL AI judge) =====
        best = await self._judge(text, groq_answer, gemini_answer)

        # ===== FIXER =====
        fixed = await self._fix(text, best)

        # ===== VERIFIER (КРИТИЧЕСКИЙ СЛОЙ) =====
        if not self.verifier.check(fixed):
            fixed = await self._fix(
                text,
                f"""
The previous answer is physically or mathematically incorrect.

Question:
{text}

Wrong answer:
{fixed}

Please correct it strictly using correct physics laws.
"""
            )

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
    # JUDGE (умный, НЕ по длине)
    # =========================

    async def _judge(self, question, a1, a2):
        prompt = f"""
You are a strict evaluator.

Question:
{question}

Answer A:
{a1}

Answer B:
{a2}

Task:
- Check correctness
- Check physics/math validity
- Choose the better answer

Return ONLY the best answer.
"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)

        return res.text

    # =========================
    # FIXER
    # =========================

    async def _fix(self, question, answer):
        prompt = f"""
You are a precision correction system.

Question:
{question}

Draft answer:
{answer}

Task:
- fix errors
- improve correctness
- ensure physical/mathematical validity
- return ONLY final answer
"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)

        return res.text