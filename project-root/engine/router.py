from engine.llm import LLMEngine

llm = LLMEngine()


class Router:
    async def handle(self, text: str) -> str:
        text = (text or "").strip()

        # простая логика маршрутизации (пока минимальная)
        return await llm.generate(text)