from app.engine.model_router import ModelRouter
from app.llm import LLM


class Orchestrator:
    def __init__(self):
        self.router = ModelRouter()
        self.llm = LLM()

    async def handle(self, user_input: str, mode: str = "fast") -> str:
        model = self.router.select(mode)

        response = await self.llm(
            prompt=user_input,
            model=model
        )

        return response