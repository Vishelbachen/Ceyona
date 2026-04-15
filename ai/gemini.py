import os
import httpx
from ai.base import BaseAIModel


class GeminiModel(BaseAIModel):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def generate(self, prompt: str, stream: bool = False):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]