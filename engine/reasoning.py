from engine.prompt import PromptTemplates


class ReasoningEngine:
    async def process(self, input_text: str, memory: str, model, route: str):

        prompt = PromptTemplates.reasoning_prompt(
            memory=memory,
            input_text=input_text
        )

        return await model.generate(prompt)