import os
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Embeddings:
    async def embed(self, text: str):
        url = "https://api.openai.com/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }

        json_data = {
            "input": text,
            "model": "text-embedding-3-small"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=json_data)

        data = response.json()
        return data["data"][0]["embedding"]

    def similarity(self, vec1, vec2):
        import math

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot / (norm1 * norm2)