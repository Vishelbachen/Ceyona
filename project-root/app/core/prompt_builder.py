class PromptBuilder:
    """
    Centralized prompt construction layer (PRODUCTION v2).

    Responsibilities:
    - strict behavior enforcement
    - multilingual output support
    - context injection
    - model behavior abstraction (NOT model names)
    - prevent AI self-identification and meta-talk
    """

    # 🧠 behavior mapping (IMPORTANT FIX)
    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:

        user_text = user_text or ""

        # 🧠 safe context rendering
        if not context:
            context_block = "EMPTY"
        else:
            context_block = "\n".join(
                f"[{msg.get('role', 'unknown').upper()}] {msg.get('text', '')}"
                for msg in context
            )

        # 🌍 MULTILINGUAL + STRICT BEHAVIOR CONTRACT
        system_block = (
            "You are a response system.\n"
            "You do NOT have identity.\n"
            "You must NEVER mention AI, assistant, model, system or architecture.\n"
            "You must NEVER explain how you work.\n"
            "You must NEVER use meta commentary.\n"
            "You must answer directly and naturally.\n"
            "You must strictly follow the language of the user input.\n"
            "If user writes in Russian, answer in Russian. If English, answer in English.\n"
            "Be concise unless detail is requested.\n"
            "Do not add emotional symbols unless user explicitly uses them.\n"
        )

        # 🧠 derive safe mode instead of exposing model name
        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model),
            "GENERAL MODE"
        )

        # 🔥 unified prompt format (SAFE VERSION)
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONVERSATION HISTORY:\n{context_block}\n\n"
            f"USER INPUT:\n{user_text}\n"
        )

    @staticmethod
    def _infer_mode(model: str) -> str:
        """
        Converts real model name → safe behavioral category
        (prevents leakage like groq/compound-mini)
        """

        model = (model or "").lower()

        # FAST MODELS
        if any(x in model for x in ["mini", "instant", "compound"]):
            return "fast"

        # HEAVY / REASONING MODELS
        if any(x in model for x in ["70b", "120b", "scout", "llama-4"]):
            return "reasoning"

        # SAFETY MODELS
        if "safeguard" in model or "guard" in model:
            return "safety"

        # CREATIVE / GENERAL
        if any(x in model for x in ["qwen", "gpt-oss", "llama-3"]):
            return "general"

        return "general"