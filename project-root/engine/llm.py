import os
from groq import Groq
from google import genai

# =========================
# MEMORY IMPORT (SAFE)
# =========================
try:
    from engine.memory.retriever import get_memory
except Exception as e:
    print("Memory disabled:", e)
    get_memory = None


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.gemini_client = None

        if self.gemini_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print("Gemini init failed:", e)
                self.gemini_client = None

    # =========================
    # CONTEXT BUILDER
    # =========================
    def _build_context(self, user_id: str, text: str) -> str:
        memory_context = ""

        if user_id and get_memory:
            try:
                memory = get_memory(user_id, limit=10) or []

                memory_lines = []
                for m in memory:
                    if isinstance(m, dict):
                        content = m.get("content")
                        if isinstance(content, str):
                            memory_lines.append(content)

                memory_context = "\n".join(memory_lines).strip()

            except Exception as e:
                print("Memory error:", e)

        if not memory_context:
            return text

        return f"""[MEMORY]
{memory_context}

[USER MESSAGE]
{text}
"""

    # =========================
    # MAIN GENERATE
    # =========================
    async def generate(self, text: str, user_id: str = None) -> str:

        if user_id:
            user_id = str(user_id)
            try:
                text = self._build_context(user_id, text)
            except Exception as e:
                print("Context error:", e)

        groq_answer = None
        gemini_answer = None

        # =========================
        # GROQ
        # =========================
        if self.groq_key:
            try:
                groq_answer = await self._groq(text)
            except Exception as e:
                print("Groq error:", e)

        # =========================
        # GEMINI
        # =========================
        if self.gemini_client:
            try:
                gemini_answer = await self._gemini(text)
            except Exception as e:
                print("Gemini error:", e)

        # =========================
        # FALLBACKS
        # =========================
        if groq_answer and not gemini_answer:
            return f"🧠 GROQ:\n{groq_answer}"

        if gemini_answer and not groq_answer:
            return f"✨ GEMINI:\n{gemini_answer}"

        if not groq_answer and not gemini_answer:
            return "❌ No models available"

        # =========================
        # DECISION
        # =========================
        if len(str(groq_answer)) >= len(str(gemini_answer)):
            return f"🔥 GROQ:\n{groq_answer}"
        else:
            return f"🔥 GEMINI:\n{gemini_answer}"

    # =========================
    # GROQ CALL
    # =========================
    async def _groq(self, text: str) -> str:
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )

        return res.choices[0].message.content

    # =========================
    # GEMINI CALL
    # =========================
    async def _gemini(self, text: str) -> str:
        response = self.gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=text
        )
        return response.text