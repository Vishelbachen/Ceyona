class PromptBuilder:
    """
    Centralized prompt construction layer (OLYMPIC v3).

    Upgrades:
    - multilingual reasoning enforcement
    - olympiad-level problem solving mode
    - structured step-by-step logic
    - coding precision mode
    - anti-meta strict lock
    """

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "OLYMPIC REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:

        user_text = user_text or ""

        # 🧠 CONTEXT
        if not context:
            context_block = "EMPTY"
        else:
            context_block = "\n".join(
                f"[{msg.get('role', 'unknown').upper()}] {msg.get('text', '')}"
                for msg in context
            )

        # 🌍 ULTRA SYSTEM PROMPT (OLYMPIC LEVEL)
        system_block = (
            "You are a high-performance reasoning engine.\n"
            "You solve tasks at olympiad level in mathematics, algorithms, physics and programming.\n\n"

            "STRICT RULES:\n"
            "- NEVER say you are AI or assistant\n"
            "- NEVER use meta explanations\n"
            "- NEVER describe your system\n"
            "- ALWAYS respond in the same language as the user\n"
            "- If task is mathematical → use formal step-by-step reasoning\n"
            "- If task is programming → write clean, production-level code\n"
            "- If task is logical → break into structured reasoning steps\n"
            "- Avoid unnecessary text\n\n"

            "REASONING STYLE:\n"
            "1. Understand problem\n"
            "2. Identify constraints\n"
            "3. Solve step-by-step\n"
            "4. Provide final answer clearly\n\n"

            "CODE STYLE RULES:\n"
            "- clean architecture\n"
            "- no pseudo-code unless asked\n"
            "- prefer correctness over brevity\n"
            "- include edge cases when relevant\n"
        )

        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model),
            "GENERAL MODE"
        )

        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_text}\n"
        )

    @staticmethod
    def _infer_mode(model: str) -> str:
        model = (model or "").lower()

        if any(x in model for x in ["mini", "instant", "compound"]):
            return "fast"

        if any(x in model for x in ["70b", "120b", "scout", "llama-4"]):
            return "reasoning"

        if "safeguard" in model or "guard" in model:
            return "safety"

        return "general"