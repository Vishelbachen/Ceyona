class PromptBuilder:
    """
    Centralized prompt construction layer (v3.5 FINAL FIXED).

    Features:
    - safe hybrid context handling (dict + dataclass)
    - stable language detection
    - task-aware reasoning mode
    - safe optional reasoning protocol injection
    - production-safe LLM prompt builder
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
    # LANGUAGE DETECTION (ROBUST)
    # -------------------------
    @staticmethod
    def _detect_language(text: str) -> str:
        if not text:
            return "en"

        text = text.strip()

        cyrillic = sum(1 for c in text if "а" <= c.lower() <= "я")
        latin = sum(1 for c in text if c.isascii() and c.isalpha())

        total = cyrillic + latin

        if total == 0:
            return "en"

        if cyrillic / total > 0.4:
            return "ru"

        return "en"

    # -------------------------
    # CONTEXT NORMALIZATION (SAFE HYBRID)
    # -------------------------
    @staticmethod
    def _clean_context(context: list, limit: int = 10) -> str:
        if not context:
            return "EMPTY"

        trimmed = context[-limit:]
        lines = []

        for msg in trimmed:

            role = None
            text = None

            # dict support
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                text = msg.get("text", "")

            # dataclass / object support
            else:
                role = getattr(msg, "role", "user")
                text = getattr(msg, "text", "")

            role = (role or "user").upper()
            text = (text or "").strip()

            if text:
                lines.append(f"{role}: {text}")

        return "\n".join(lines) if lines else "EMPTY"

    # -------------------------
    # MODE INFERENCE (TASK PRIORITY)
    # -------------------------
    @staticmethod
    def _infer_mode(model: str, task: str = None) -> str:
        model = (model or "").lower()
        task = (task or "").lower()

        # task overrides model
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
    # MAIN BUILD FUNCTION
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

        # -------------------------
        # SYSTEM BLOCK
        # -------------------------
        system_block = (
            "You are a high-level reasoning system.\n"
            "You produce accurate, structured answers.\n"
            "Avoid hallucination.\n"
            "Be concise and logically consistent.\n"
        )

        # -------------------------
        # TASK BLOCK
        # -------------------------
        reasoning_block = f"TASK: {task_type.upper()}"

        # -------------------------
        # OPTIONAL REASONING PROTOCOL
        # -------------------------
        protocol_block = ""
        if reasoning_protocol:
            rp = reasoning_protocol.strip()
            if rp:
                protocol_block = f"REASONING PROTOCOL:\n{rp}\n"

        # -------------------------
        # LANGUAGE BLOCK
        # -------------------------
        lang_block = (
            "RESPONSE LANGUAGE:\n"
            f"- primary language: {lang}\n"
            "- natural adaptation\n"
            "- do not mention language detection\n"
        )

        # -------------------------
        # FINAL PROMPT
        # -------------------------
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
            f"{protocol_block}"
            f"{lang_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_text}\n"
        )