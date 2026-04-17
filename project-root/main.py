import os
import importlib
from groq import Groq

# =========================
# SAFE MEMORY IMPORT
# =========================
get_memory = None

try:
    memory_module = importlib.import_module("engine.memory.retriever")
    get_memory = getattr(memory_module, "get_memory", None)
except Exception as e:
    print("Memory disabled:", e)
    get_memory = None


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")

        # Gemini intentionally DISABLED for stability (fix later)
        self.gemini_enabled = False

    # =========================
    # MEMORY CONTEXT
    # =========================
    def _build_context(self, user_id: str, text: str) -> str:
        memory_context = ""

        if user_id and get_memory:
            try:
                memory = get_memory(user_id, limit=10) or []

                lines = []
                for m in memory:
                    if isinstance(m, dict):
                        c = m.get("content")
                        if isinstance(c, str) and len(c) < 500:
                            lines.append(c)

                memory_context = "\n".join(lines).strip()

            except Exception as e:
                print("Memory error:", e)

        if not memory_context:
            return text

        return f"""[MEMORY]
{memory_context}

[USER]
{text}
"""

    # =========================
    # MAIN GENERATE
    # =========================
    async def generate(self, text: str, user_id: str = None) -> str:

        if user_id:
            user_id = str(user_id)
            text = self._build_context(user_id, text)

        if not self.groq_key:
            return "❌ GROQ_API_KEY missing"

        try:
            return await self._groq(text)
        except Exception as e:
            return f"❌ LLM ERROR: {e}"

    # =========================
    # GROQ (MAIN ENGINE)
    # =========================
    async def _groq(self, text: str) -> str:
        client = Groq(api_key=self.groq_key)

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return res.choices[0].message.content