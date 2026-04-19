class PromptBuilder:

    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:
        context_block = "\n".join(
            f"{msg['role']}: {msg['text']}" for msg in context
        )

        return f"""
USER INPUT:
{user_text}

CONTEXT:
{context_block}

MODEL:
{model}
"""