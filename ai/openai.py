import os
import httpx
from ai.base import BaseAIModel


class OpenAIModel(BaseAIModel):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.url = "https://api.openai.com/v1/chat/completions"

    async def generate(self, prompt: str, stream: bool = False):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.url, json=payload, headers=headers)

        data = response.json()

        return data["choices"][0]["message"]["content"]