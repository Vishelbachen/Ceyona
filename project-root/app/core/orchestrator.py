from ..engine.model_router import ModelRouter
from ..llm import LLM


class Orchestrator:
    def __init__(self):
        self.router = ModelRouter()
        self.llm = LLM()

    async def handle(self, text: str) -> str:
        model = await self.router.select_model(text)
        result = await self.llm.generate(model=model, prompt=text)
        return result