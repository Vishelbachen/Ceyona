class Router:
    def __init__(self):
        pass

    async def handle(self, text: str) -> str:
        text = (text or "").lower()

        if "привет" in text:
            return "Привет 👋 я уже с мозгами"

        if "как дела" in text:
            return "Работаю стабильно и уже умнее 😏"

        return f"[Router] Ты написал: {text}"