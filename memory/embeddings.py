from openai import AsyncOpenAI


class Embeddings:
    def __init__(self, settings):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def embed(self, text: str) -> list:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding