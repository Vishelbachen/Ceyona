from engine.reason import Reason


class Reasoning:
    def __init__(self):
        self.reason = Reason()

    async def analyze(self, text: str, context: dict, route: dict, brain: dict = None) -> dict:
        base = self.reason.analyze(text)

        return {
            "base": base,
            "route": route,
            "brain": brain or {"domain": "general"},
            "complexity": "high" if len(text) > 50 else "low"
        }