from engine.tool_chain import ToolChain


class ReasoningEngine:
    def __init__(self):
        self.tool_chain = ToolChain()

    async def process(self, input_text: str, memory: str, model, route: str):
        prompt = f"""
You are advanced reasoning system.

Memory:
{memory}

Task:
{input_text}

Return best possible answer.
"""

        response = await model.generate(prompt)

        return response