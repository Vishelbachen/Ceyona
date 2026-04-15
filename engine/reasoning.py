class ReasoningEngine:
    async def process(self, input_text: str, memory: str, model, route: str):
        prompt = self._build_prompt(input_text, memory, route)

        response = await model.generate(prompt)

        return response

    def _build_prompt(self, input_text: str, memory: str, route: str):
        system = f"""
You are an advanced AI system.

Route: {route}

Use memory context if relevant:
{memory}

Think step by step internally but provide clean final answer.
"""

        return f"{system}\nUser: {input_text}"