from engine.prompt import PromptBuilder


class Solver:
    def __init__(self):
        self.prompt = PromptBuilder()

    async def solve(self, text, context, reasoning, route):
        prompt = self.prompt.build(text, context, reasoning)

        # временно без AI (дальше подключим selector)
        return f"[Ceyona AI]\n{prompt}"