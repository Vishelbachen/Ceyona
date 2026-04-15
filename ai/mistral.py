import httpx


class MistralClient:
    def __init__(self, settings):
        self.api_key = settings.MISTRAL_API_KEY
        self.url = "https://api.mistral.ai/v1/chat/completions"

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": "mistral-small",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]