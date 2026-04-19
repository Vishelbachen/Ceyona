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
                f"[{msg.get('role', 'unknown').upper()}] {msg.get('text', '')}"
                for msg in context
            )

        # 🧠 system framing (VERY IMPORTANT FOR MODEL STABILITY)
        system_block = (
            "You are a helpful AI assistant.\n"
            "Follow instructions precisely.\n"
            "Be concise when possible.\n"
        )

        # 🔥 unified prompt format
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"CONVERSATION HISTORY:\n{context_block}\n\n"
            f"USER INPUT:\n{user_text}\n\n"
            f"TARGET MODEL:\n{model}\n"
        )