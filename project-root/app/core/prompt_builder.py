class PromptBuilder:
    """
    Centralized prompt construction layer (v3.3).

    Improvements:
    - adaptive reasoning system
    - multilingual control
    - softer safety constraints
    - better task detection
    - reduced prompt rigidity
    """

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "DEEP REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    # -------------------------
    # LANGUAGE DETECTION (lightweight)
    # -------------------------
    @staticmethod
    def _detect_language(text: str) -> str:
        t = (text or "").lower()

        russian_chars = any("а" <= c <= "я" for c in t)
        if russian_chars:
            return "ru"

        return "en"

    # -------------------------
    # TASK DETECTION (IMPROVED)
    # -------------------------
    @staticmethod
    def _detect_task(text: str) -> str:
        t = (text or "").lower()

        # math / physics
        if any(x in t for x in [
            "integral", "derivative", "equation",
            "force", "energy", "mass", "velocity",
            "solve", "calculate"
        ]):
            return "math_physics"

        # coding
        if any(x in t for x in [
            "code", "function", "algorithm",
            "class", "bug", "debug"
        ]):
            return "coding"

        # proof / logic
        if any(x in t for x in [
            "prove", "theorem", "show that",
            "why", "logic"
        ]):
            return "reasoning"

        # analysis / history / explanation
        if any(x in t for x in [
            "history", "explain", "when",
            "what happened", "why did"
        ]):
            return "analysis"

        return "general"

    # -------------------------
    # CONTEXT CLEANER (IMPROVED)
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

            if len(text) < 1:
                continue

            cleaned.append(f"{role}: {text}")

        return "\n".join(cleaned) if cleaned else "EMPTY"

    # -------------------------
    # MAIN BUILD
    # -------------------------
    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:

        user_text = (user_text or "").strip()

        lang = PromptBuilder._detect_language(user_text)
        task = PromptBuilder._detect_task(user_text)

        context_block = PromptBuilder._clean_context(context)

        # -------------------------
        # SYSTEM CORE (SOFTENED)
        # -------------------------
        system_block = (
            "You are a high-level reasoning system.\n"
            "You produce accurate, structured and helpful answers.\n\n"

            "GENERAL BEHAVIOR:\n"
            "- adapt tone naturally\n"
            "- avoid unnecessary repetition\n"
            "- prioritize clarity and correctness\n\n"

            "QUALITY GUIDELINES:\n"
            "- think step by step when needed\n"
            "- avoid filler or vague explanations\n"
            "- use structured reasoning for complex tasks\n"
        )

        # -------------------------
        # TASK ROUTING BLOCK
        # -------------------------
        if task == "math_physics":
            reasoning_block = (
                "TASK: MATHEMATICS / PHYSICS\n"
                "Approach:\n"
                "1. identify known values\n"
                "2. select correct formula\n"
                "3. derive step-by-step\n"
                "4. compute carefully\n"
                "5. present final answer\n"
            )

        elif task == "coding":
            reasoning_block = (
                "TASK: PROGRAMMING\n"
                "Approach:\n"
                "1. understand problem\n"
                "2. design solution\n"
                "3. write clean code\n"
                "4. consider edge cases\n"
                "5. verify correctness\n"
            )

        elif task == "reasoning":
            reasoning_block = (
                "TASK: LOGICAL REASONING\n"
                "Approach:\n"
                "1. understand statement\n"
                "2. break into steps\n"
                "3. apply logic carefully\n"
                "4. conclude precisely\n"
            )

        elif task == "analysis":
            reasoning_block = (
                "TASK: ANALYSIS\n"
                "Approach:\n"
                "1. identify key facts\n"
                "2. structure explanation\n"
                "3. support reasoning\n"
                "4. conclude clearly\n"
            )

        else:
            reasoning_block = (
                "TASK: GENERAL\n"
                "Approach:\n"
                "1. understand question\n"
                "2. think logically\n"
                "3. respond clearly\n"
            )

        # -------------------------
        # MODE SIGNAL
        # -------------------------
        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model),
            "GENERAL MODE"
        )

        # -------------------------
        # LANGUAGE CONTROL
        # -------------------------
        lang_block = f"OUTPUT LANGUAGE: {lang.upper()}"

        # -------------------------
        # FINAL PROMPT
        # -------------------------
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
            f"{lang_block}\n"
            f"MODE:\n{mode}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_text}\n"
        )

    # -------------------------
    # MODEL INFERENCE
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