class ModelRouter:
    async def select_model(self, text: str) -> str:
        return "llama3-8b-8192"