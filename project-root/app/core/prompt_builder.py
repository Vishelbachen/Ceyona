class PromptBuilder:
    """
    Centralized prompt construction layer (v3.5 stable).

    Fixes:
    - orchestrator compatibility
    - context type safety
    - reasoning engine integration
    - task-aware prompting
    """

    # -------------------------
    # MODEL MODES
    # -------------------------
    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "DEEP REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    # -------------------------
    # LANGUAGE DETECTION
    # -------------------------
    @staticmethod
    def _detect_language(text: str) -> str:
        if not text:
            return "en"

        text = text.strip()

        cyrillic = sum(1 for c in text if "а" <= c.lower() <= "я")
        latin = sum(1 for c in text if c.isascii() and c.isalpha())

        if cyrillic > 0 and cyrillic >= latin:
            return "ru"

        return "en"

    # -------------------------
    # CONTEXT NORMALIZATION (FIXED)
    # -------------------------
    @staticmethod
    def _clean_context(context: list, limit: int = 10) -> str:

        if not context:
            return "EMPTY"

        trimmed = context[-limit:]

        lines = []

        for msg in trimmed:

            # supports dict OR dataclass
            role = getattr(msg, "role", None) or msg.get("role", "user")
            text = getattr(msg, "text", None) or msg.get("text", "")

            text = (text or "").strip()

            if text:
                lines.append(f"{str(role).upper()}: {text}")

        return "\n".join(lines) if lines else "EMPTY"

    # -------------------------
    # MODE INFERENCE
    # -------------------------
    @staticmethod
    def _infer_mode(model: str, task: str = None) -> str:

        model = (model or "").lower()
        task = (task or "").lower()

        # PRIORITY: task > model

        if task in ["math", "physics", "coding", "reasoning"]:
            return "reasoning"

        if task in ["creative", "writing"]:
            return "creative"

        if any(x in model for x in ["mini", "instant", "compound"]):
            return "fast"

        if any(x in model for x in ["70b", "120b", "llama-4", "scout"]):
            return "reasoning"

        if "guard" in model or "safety" in model:
            return "safety"

        return "general"

    # -------------------------
    # MAIN BUILD (FIXED)
    # -------------------------
    @staticmethod
    def build(
        user_text: str,
        context: list,
        model: str,
        task_type: str = "general",
        reasoning_protocol: str = None,
    ) -> str:

        user_text = (user_text or "").strip()
        lang = PromptBuilder._detect_language(user_text)

        context_block = PromptBuilder._clean_context(context)

        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model, task_type),
            "GENERAL MODE"
        )

        system_block = (
            "You are a high-level reasoning system.\n"
            "You produce accurate, structured answers.\n"
            "Avoid hallucination.\n"
            "Be concise and logically consistent.\n"
        )

        reasoning_block = f"TASK: {task_type.upper()}"

        protocol_block = (
            f"REASONING PROTOCOL:\n{reasoning_protocol}\n"
            if reasoning_protocol else ""
        )

        lang_block = (
            "RESPONSE LANGUAGE:\n"
            f"- primary language: {lang}\n"
            "- natural adaptation\n"
            "- no mention of language detection\n"
        )

        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
            f"{protocol_block}\n"
            f"{lang_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_text}\n"
        )