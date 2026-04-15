class Orchestrator:
    def __init__(self):
        pass

    async def process(self, user_id: int, text: str) -> str:
        # временно базовый ответ (дальше подключим AI)
        return f"[Ceyona] You said: {text}"