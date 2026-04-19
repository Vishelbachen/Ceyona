class PromptBuilder:
    """
    Centralized prompt construction layer.

    Responsibilities:
    - isolate prompt formatting from orchestrator
    - unify input structure for all models
    - prepare context-safe prompt
    """

    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:
        # 🧠 safe context rendering
        if not context:
            context_block = "EMPTY"
        else:
            context_block = "\n".join(
                f"{msg.get('role', 'unknown')}: {msg.get('text', '')}"
                for msg in context
            )

        # 🔥 unified prompt format
        return (
            f"USER INPUT:\n{user_text}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"TARGET MODEL:\n{model}\n"
        )