from engine.llm import LLMEngine

llm = LLMEngine()


class Router:
    async def handle(self, text: str) -> str:
        return await llm.generate(text)