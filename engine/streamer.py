import asyncio


class Streamer:
    async def stream(self, text: str, chunk_size: int = 20):
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            await asyncio.sleep(0.01)
            yield chunk