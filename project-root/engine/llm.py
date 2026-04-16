import os


class LLMEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    async def generate(self, text: str) -> str:
        text = text or ""

        # временно НЕ используем OpenAI вообще

        if self.groq_key:
            return await self._groq(text)

        if self.gemini_key:
            return await self._gemini(text)

        return "❌ No LLM configured (Groq / Gemini missing)"

    async def _groq(self, text: str) -> str:
        try:
            from groq import Groq

            client = Groq(api_key=self.groq_key)

            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": text}
                ]
            )

            return res.choices[0].message.content

        except Exception as e:
            return f"❌ GROQ ERROR: {str(e)}"

    async def _gemini(self, text: str) -> str:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_key)

            model = genai.GenerativeModel("gemini-1.5-flash")

            res = model.generate_content(text)

            return res.text

        except Exception as e:
            return f"❌ GEMINI ERROR: {str(e)}"