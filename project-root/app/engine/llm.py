import os
from groq import Groq


class LLM:
    def __init__(self):
        self._client = None

    def client(self):
        if self._client is None:
            self._client = Groq(
                api_key=os.getenv("GROQ_API_KEY")
            )
        return self._client

    async def __call__(self, prompt: str, model: str) -> str:
        try:
            response = self.client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"LLM_ERROR: {str(e)}"