import os
from groq import Groq


class LLM:
    def __init__(self):
        self.client = None

    def _client(self):
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY missing")
            self.client = Groq(api_key=api_key)
        return self.client

    async def __call__(self, prompt: str, model: str) -> str:
        try:
            response = self._client().chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content

        except Exception as e:
            return f"LLM_ERROR: {str(e)}"