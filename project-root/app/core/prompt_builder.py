class PromptBuilder:
    """
    Centralized prompt construction layer (OLYMPIC v3.2).

    Upgrades:
    - reasoning-aware prompting
    - olympiad-level enforcement boost
    - task-type adaptive structure
    - multilingual strict mode
    - conversation anti-loop fix (IMPORTANT)
    """

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "OLYMPIC REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    # 🧠 TASK DETECTION
    @staticmethod
    def _detect_task(text: str) -> str:
        t = (text or "").lower()

        if any(x in t for x in ["integral", "derivative", "force", "energy", "mass", "velocity"]):
            return "math_physics"

        if any(x in t for x in ["code", "function", "algorithm", "bug", "class"]):
            return "coding"

        if any(x in t for x in ["prove", "show that", "theorem"]):
            return "proof"

        if any(x in t for x in ["history", "war", "empire", "why did", "when"]):
            return "analysis"

        return "general"

    @staticmethod
    def build(user_text: str, context: list, model: str) -> str:

        user_text = user_text or ""

        # 🧠 CONTEXT SAFE BUILD
        if not context:
            context_block = "EMPTY"
        else:
            context_block = "\n".join(
                f"[{msg.get('role', 'unknown').upper()}] {msg.get('text', '')}"
                for msg in context
            )

        # 🧠 TASK DETECTION
        task = PromptBuilder._detect_task(user_text)

        # 🌍 SYSTEM CORE (FIXED: anti-loop + conversational stability)
        system_block = (
            "You are a high-level reasoning engine.\n"
            "You solve problems at olympiad and research level.\n\n"

            "CONVERSATION RULES (IMPORTANT FIX):\n"
            "- Do NOT repeat generic phrases like 'How can I help you?'\n"
            "- Respond naturally based on context\n"
            "- If user is casual → be casual\n"
            "- If user is confused → clarify instead of repeating templates\n\n"

            "ABSOLUTE RULES:\n"
            "- NEVER mention AI, assistant, model, system\n"
            "- NEVER describe internal architecture\n"
            "- NEVER use meta explanations\n"
            "- ALWAYS match user language\n\n"

            "QUALITY RULES:\n"
            "- prioritize correctness over speed\n"
            "- use structured reasoning when needed\n"
            "- avoid filler text\n"
        )

        # 🧠 REASONING BLOCK (TASK-SPECIFIC)
        if task == "math_physics":
            reasoning_block = (
                "REASONING MODE: MATHEMATICS / PHYSICS\n"
                "1. Identify known quantities\n"
                "2. Choose correct law/formula\n"
                "3. Derive step-by-step\n"
                "4. Compute carefully\n"
                "5. Present final answer clearly\n"
            )

        elif task == "coding":
            reasoning_block = (
                "REASONING MODE: PROGRAMMING\n"
                "1. Understand requirements\n"
                "2. Design solution\n"
                "3. Implement clean code\n"
                "4. Handle edge cases\n"
                "5. Ensure correctness\n"
            )

        elif task == "proof":
            reasoning_block = (
                "REASONING MODE: PROOF\n"
                "1. Understand statement\n"
                "2. Define assumptions\n"
                "3. Build logical steps\n"
                "4. Conclude rigorously\n"
            )

        else:
            reasoning_block = (
                "REASONING MODE: GENERAL\n"
                "1. Understand question\n"
                "2. Think logically\n"
                "3. Answer clearly\n"
            )

        # 🧠 MODEL MODE
        mode = PromptBuilder.MODEL_MODES.get(
            PromptBuilder._infer_mode(model),
            "GENERAL MODE"
        )

        # 🔥 FINAL PROMPT
        return (
            f"SYSTEM:\n{system_block}\n\n"
            f"{reasoning_block}\n\n"
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