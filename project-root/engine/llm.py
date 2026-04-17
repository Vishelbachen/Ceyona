import os
from groq import Groq
from google import genai

# =========================
# USER MEMORY
# =========================
try:
    from engine.memory.retriever import get_memory
except Exception as e:
    print("Memory module not available:", e)
    get_memory = None


# =========================
# PROJECT MEMORY (NEW SAFE LAYER)
# =========================
try:
    from engine.memory.project_retriever import get_project_memory
except Exception:
    get_project_memory = None


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.gemini_client = None

        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)

    # =========================
    # CONTEXT BUILDER (SAFE)
    # =========================
    def _build_context(self, user_id: str, text: str) -> str:
        """
        Injects:
        - project memory (code/project context)
        - user memory (chat memory)
        """

        # =========================
        # PROJECT MEMORY
        # =========================
        project_context = ""
        if get_project_memory:
            try:
                pm = get_project_memory(limit=10)

                project_lines = []
                for p in pm:
                    file = p.get("file")
                    action = p.get("action")
                    content = p.get("content")

                    if file or content:
                        project_lines.append(f"{file} | {action} | {content}")

                project_context = "\n".join(project_lines).strip()

            except Exception as e:
                print("Project memory error:", e)
                project_context = ""

        # =========================
        # USER MEMORY
        # =========================
        memory_context = ""

        if user_id and get_memory:
            try:
                memory = get_memory(user_id, limit=10)
            except Exception as e:
                print("Memory error:", e)
                memory = []

            memory_lines = []
            for m in memory:
                content = m.get("content")
                if content and isinstance(content, str):
                    memory_lines.append(content)

            memory_context = "\n".join(memory_lines).strip()

        # =========================
        # FINAL CONTEXT BUILD
        # =========================
        if not project_context and not memory_context:
            return text

        return f"""
[PROJECT MEMORY]
{project_context}

[USER MEMORY]
{memory_context}

[CURRENT USER MESSAGE]
{text}
"""

    # =========================
    # MAIN GENERATE
    # =========================
    async def generate(self, text: str, user_id: str = None) -> str:

        if user_id is not None:
            user_id = str(user_id)

        if user_id:
            try:
                text = self._build_context(user_id, text)
            except Exception as e:
                print("Context build error:", e)

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