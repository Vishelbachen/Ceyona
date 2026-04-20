class PromptBuilder:
    """
    Centralized prompt construction layer (v3.4 CLEAN).
    """

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "DEEP REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    # -------------------------
    # LANGUAGE DETECTION (FIXED)
    # -------------------------
    @staticmethod
    def _detect_language(text: str) -> str:
        if not text:
            return "en"

        cyrillic = sum(1 for c in text if "а" <= c.lower() <= "я")
        latin = sum(1 for c in text if c.isascii() and c.isalpha())

        return "ru" if cyrillic > latin else "en"

    # -------------------------
    # CONTEXT CLEANER
    # -------------------------
    @staticmethod
    def _clean_context(context: list, limit: int = 10) -> str:
        if not context:
            return "EMPTY"

        trimmed = context[-limit:]

        cleaned = []
        for msg in trimmed:
            text = (msg.get("text") or "").strip()
            role = msg.get("role", "user").upper()

            if text:
                cleaned.append(f"{role}: {text}")

        return "\n".join(cleaned) if cleaned else "EMPTY"

    # -------------------------
    # MAIN BUILD (UPDATED)
    # -------------------------
    @staticmethod
    def build(
        user_text: str,
        context: list,
        model: str,
        task: str,
    ) -> str:

        user_text = (user_text or "").strip()
        lang = PromptBuilder._detect_language(user_text)

        context_block = PromptBuilder._clean_context(context)

        system_block = (
            "You are a high-level reasoning system.\n"
            "You produce accurate, structured answers.\n"
            "Avoid unnecessary repetition.\n"
            "Be concise when possible.\n"
        )

        reasoning_block = f"TASK: {task.upper()}"

        lang_block = (
            "RESPONSE LANGUAGE:\n"
            f"- primary language: {lang}\n"
            "- adapt naturally\n"
            "- do not mention language switching\n"
        )

        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model),
            "GENERAL MODE"
        )

        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
            f"{lang_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_text}\n"
        )

    # -------------------------
    # MODEL MODE INFERENCE
    # -------------------------
    @staticmethod
    def _infer_mode(model: str) -> str:
        model = (model or "").lower()

        if any(x in model for x in ["mini", "instant", "compound"]):
            return "fast"

        if any(x in model for x in ["70b", "120b", "llama-4", "scout"]):
            return "reasoning"

        if "safeguard" in model or "guard" in model:
            return "safety"

        return "general"