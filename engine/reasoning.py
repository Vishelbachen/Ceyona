from engine.prompt import PromptTemplates
from engine.tool_chain import ToolChain


class ReasoningEngine:
    """
    Core reasoning layer (ChatGPT-like LLM orchestration step)
    """

    def __init__(self):
        self.tool_chain = ToolChain()

    async def process(
        self,
        input_text: str,
        memory: str,
        model,
        route: str
    ):
        # =========================
        # PROMPT ENGINE (centralized)
        # =========================
        prompt = PromptTemplates.reasoning_prompt(
            memory=memory,
            input_text=input_text
        )

        # =========================
        # LLM CALL
        # =========================
        response = await model.generate(prompt)

        # =========================
        # OPTIONAL: TOOL-AWARE EXTENSION HOOK (future chaining)
        # =========================
        # сейчас не активируем, но архитектура уже готова
        # tools = await self.tool_chain.execute_chain(...)

        return response