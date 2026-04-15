from engine.reason import Reason


class Reasoning:
    def __init__(self):
        self.reason = Reason()

    async def analyze(self, text: str, context: dict, route: dict) -> dict:
        base = self.reason.analyze(text)

        return {
            "base": base,
            "route": route,
            "complexity": "high" if len(text) > 50 else "low"
        }