import asyncio


class Streamer:
    """
    True streaming system (ChatGPT-like behavior simulation)
    """

    async def stream_tokens(self, text: str):
        buffer = ""

        for char in text:
            buffer += char

            # emit on sentence / punctuation
            if char in ".!?," or len(buffer) >= 6:
                yield {
                    "token": buffer,
                    "done": False
                }
                await asyncio.sleep(0.005)
                buffer = ""

        if buffer:
            yield {
                "token": buffer,
                "done": True
            }