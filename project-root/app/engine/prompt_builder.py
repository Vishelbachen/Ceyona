class PromptBuilder:

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "DEEP REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    @staticmethod
    def _detect_language(text: str) -> str:
        if not text:
            return "en"

        text = text.strip().lower()

        if any(word in text for word in ["привет", "как", "что", "почему"]):
            return "ru"

        if any(word in text for word in ["the", "what", "why", "how"]):
            return "en"

        cyrillic = sum(1 for c in text if "а" <= c <= "я")
        latin = sum(1 for c in text if c.isascii() and c.isalpha())

        return "ru" if cyrillic > latin else "en"

    @staticmethod
    def _clean_context(context: list, limit: int = 10) -> str:
        if not context:
            return ""

        trimmed = context[-limit:]
        lines = []

        for msg in trimmed:

            if isinstance(msg, dict):
                role = msg.get("role", "user")
                text = msg.get("text", "")
            else:
                role = getattr(msg, "role", "user")
                text = getattr(msg, "text", "")

            role = (role or "user").upper()
            text = (text or "").strip()

            if text:
                lines.append(f"{role}: {text}")

        return "\n".join(lines)

    @staticmethod
    def _infer_mode(model: str, task: str = None) -> str:
        model = (model or "").lower()
        task = (task or "").lower()

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

        mode_key = PromptBuilder._infer_mode(model, task_type)
        mode = PromptBuilder.MODEL_MODES.get(mode_key, "GENERAL MODE")

        system_block = (
            "You are a high-level reasoning system.\n"
            "Produce accurate and structured answers.\n"
            "Avoid hallucinations.\n"
            "Be concise and logically consistent.\n"
        )

        reasoning_block = f"TASK: {task_type.upper()}"

        protocol_block = ""
        if reasoning_protocol:
            rp = reasoning_protocol.strip()
            if rp:
                protocol_block = f"REASONING PROTOCOL:\n{rp}\n"

        lang_block = (
            "RESPONSE LANGUAGE:\n"
            f"- primary language: {lang}\n"
            "- natural adaptation\n"
            "- do not mention language detection\n"
        )

        context_final = context_block if context_block else "None"

        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
            f"{protocol_block}"
            f"{lang_block}\n\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_final}\n\n"
            f"USER:\n{user_text}\n"
        )