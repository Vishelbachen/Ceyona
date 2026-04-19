class PromptBuilder:
    """
    Centralized prompt construction layer (PRODUCTION v2.1).

    Responsibilities:
    - strict behavior enforcement
    - multilingual output support
    - reasoning enhancement for complex tasks
    - context injection
    - model behavior abstraction (NOT model names)
    - prevent AI self-identification and meta-talk
    """

    # 🧠 behavior mapping (SAFE ABSTRACTION LAYER)
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

        # 🌍 MULTILINGUAL + STRICT BEHAVIOR CONTRACT (HARDENED)
        system_block = (
            "You are a reasoning and response engine.\n"
            "You do NOT have identity.\n"
            "You must NEVER mention AI, assistant, model, system or architecture.\n"
            "You must NEVER explain how you work or describe internal logic.\n"
            "You must NEVER use meta commentary.\n"
            "You must NEVER say phrases like 'I am an AI'.\n"
            "You must answer directly, clearly, and naturally.\n"
            "You must strictly match the language of the user input.\n"
            "If user writes in Russian, respond in Russian. If English, respond in English.\n"
            "Do NOT translate unless asked.\n"
            "Be concise by default, but expand if reasoning is required.\n"
            "Avoid filler phrases and unnecessary explanations.\n"
        )

        # 🧠 MODE SELECTION (SAFE BEHAVIOR ABSTRACTION)
        mode_key = PromptBuilder._infer_mode(model)
        mode = PromptBuilder.MODEL_MODES.get(mode_key, "GENERAL MODE")

        # 🧠 REASONING BOOST (ONLY FOR COMPLEX TASKS)
        reasoning_boost = ""
        if mode_key == "reasoning":
            reasoning_boost = (
                "\nREASONING RULES:\n"
                "- Think step-by-step before answering\n"
                "- Verify correctness internally\n"
                "- Prefer logical structure\n"
                "- Do not skip steps in mathematical or olympiad tasks\n"
            )

        # 🔥 unified prompt format (HARDENED)
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"MODE:\n{mode}\n"
            f"{reasoning_boost}\n"
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

        # ⚡ FAST MODE
        if any(x in model for x in ["mini", "instant", "compound"]):
            return "fast"

        # 🧠 REASONING / HEAVY MODE
        if any(x in model for x in ["70b", "120b", "scout", "llama-4"]):
            return "reasoning"

        # 🛡 SAFETY MODE
        if "safeguard" in model or "guard" in model:
            return "safety"

        # 🎨 GENERAL / CREATIVE MODE
        if any(x in model for x in ["qwen", "gpt-oss", "llama-3"]):
            return "general"

        return "general"