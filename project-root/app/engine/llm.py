import os
from groq import AsyncGroq


class LLM:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def generate(self, model: str, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content