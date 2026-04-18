from ..engine.model_router import ModelRouter
from ..llm import LLM


class Orchestrator:
    def __init__(self):
        self.router = ModelRouter()
        self.llm = LLM()

    async def handle(self, text: str) -> str:
        model = self.router.select("fast")

        result = await self.llm(
            prompt=text,
            model=model
        )

        return result