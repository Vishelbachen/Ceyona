class PromptBuilder:
    """
    Centralized prompt construction layer (OLYMPIC v3.1).

    Upgrades:
    - reasoning-aware prompting
    - olympiad-level enforcement boost
    - task-type adaptive structure
    - multilingual strict mode
    """

    MODEL_MODES = {
        "fast": "FAST MODE",
        "general": "GENERAL MODE",
        "reasoning": "OLYMPIC REASONING MODE",
        "creative": "CREATIVE MODE",
        "safety": "SAFETY MODE",
    }

    # 🧠 lightweight task inference (NO NEW FILE NEEDED)
    @staticmethod
    def _detect_task(text: str) -> str:
        t = (text or "").lower()

        if any(x in t for x in ["integral", "derivative", "force", "energy", "mass", "velocity"]):
            return "math_physics"

        if any(x in t for x in ["code", "function", "algorithm", "bug", "class"]):
            return "coding"

        if any(x in t for x in ["prove", "show that", "prove that", "theorem"]):
            return "proof"

        if any(x in t for x in ["history", "when", "why did", "war", "empire"]):
            return "analysis"

        return "general"

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

        # 🧠 TASK DETECTION
        task = PromptBuilder._detect_task(user_text)

        # 🌍 SYSTEM CORE
        system_block = (
            "You are a high-level reasoning engine.\n"
            "You solve problems at olympiad and research level.\n\n"

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

        # 🧠 TASK-BASED REASONING BOOST (KEY FIX)
        reasoning_block = ""

        if task == "math_physics":
            reasoning_block = (
                "REASONING MODE: MATHEMATICS / PHYSICS\n"
                "Step 1: Identify known quantities\n"
                "Step 2: Choose physical/mathematical law\n"
                "Step 3: Derive equations step-by-step\n"
                "Step 4: Solve carefully\n"
                "Step 5: Final answer clearly boxed\n"
            )

        elif task == "coding":
            reasoning_block = (
                "REASONING MODE: PROGRAMMING\n"
                "Step 1: Understand requirements\n"
                "Step 2: Design solution structure\n"
                "Step 3: Write clean code\n"
                "Step 4: Consider edge cases\n"
                "Step 5: Ensure correctness\n"
            )

        elif task == "proof":
            reasoning_block = (
                "REASONING MODE: PROOF\n"
                "Step 1: Understand statement\n"
                "Step 2: Define known properties\n"
                "Step 3: Build logical chain\n"
                "Step 4: Derive conclusion rigorously\n"
            )

        else:
            reasoning_block = (
                "REASONING MODE: GENERAL\n"
                "Step 1: Understand question\n"
                "Step 2: Think logically\n"
                "Step 3: Answer clearly\n"
            )

        # 🧠 MODEL MODE (safe abstraction)
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