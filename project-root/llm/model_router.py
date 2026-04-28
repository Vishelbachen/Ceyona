class ModelRouter:
    """
    v4.7 LLM routing layer
    """

    def generate(self, prompt: str, context: list[str]) -> str:
        return f"[MOCK RESPONSE] {prompt} | context={len(context)}"