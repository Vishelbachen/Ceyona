import asyncio


class Streamer:
    async def stream_tokens(self, text: str, chunk_size: int = 5):
        """
        Simulates token-by-token streaming like ChatGPT
        """

        buffer = ""

        for char in text:
            buffer += char

            if len(buffer) >= chunk_size or char in [".", ",", "!", "?"]:
                yield buffer
                await asyncio.sleep(0.01)
                buffer = ""

        if buffer:
            yield buffer