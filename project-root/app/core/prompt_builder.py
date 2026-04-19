class PromptBuilder:
    """
    Centralized prompt construction layer.

    Responsibilities:
    - isolate prompt formatting
    - enforce strict model behavior contract
    - prevent self-identification and meta-talk
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

        # 🔥 STRICT SYSTEM CONTRACT (IMPORTANT FIX)
        system_block = (
            "You are a response engine.\n"
            "You must NOT mention that you are an AI, model, assistant or system.\n"
            "You must NOT explain your behavior or capabilities.\n"
            "You must NOT use phrases like 'I am an AI'.\n"
            "You must answer directly without meta commentary.\n"
            "Follow user instructions precisely.\n"
            "Keep responses natural and human-like.\n"
            "Match the language of the user input.\n"
            "Be concise unless detail is explicitly requested.\n"
        )

        # 🔥 unified prompt format
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"CONVERSATION HISTORY:\n{context_block}\n\n"
            f"USER INPUT:\n{user_text}\n\n"
            f"TARGET MODEL:\n{model}\n"
        )