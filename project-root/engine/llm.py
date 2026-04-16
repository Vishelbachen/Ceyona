class LLMEngine:
    ...
    async def _groq(self, text: str) -> str:
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_key)

            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": text}]
            )

            return "[GROQ] " + res.choices[0].message.content

        except Exception as e:
            return f"[GROQ ERROR] {str(e)}"