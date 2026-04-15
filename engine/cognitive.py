class Cognitive:
    async def build_context(self, user_id: int, text: str) -> dict:
        return {
            "user_id": user_id,
            "input": text,
            "history": []  # сюда подключится memory
        }