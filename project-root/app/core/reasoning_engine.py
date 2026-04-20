class ReasoningEngine:
    """
    Unified reasoning strategy layer (v2.2 FIXED + production stable).

    Role:
    - defines HOW to solve (not what)
    - generates structured reasoning protocol
    - safe for prompt injection into LLM pipeline
    """

    # -------------------------
    # NORMALIZATION
    # -------------------------
    @staticmethod
    def _norm(value: str) -> str:
        return (value or "").strip().lower()

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    @staticmethod
    def get_protocol(task_type: str, complexity: str = "medium", language: str = "en") -> str:

        task_type = ReasoningEngine._norm(task_type) or "general"
        complexity = ReasoningEngine._norm(complexity) or "medium"
        language = ReasoningEngine._norm(language) or "en"

        # -------------------------
        # SCIENCE / MATH DOMAIN
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            if complexity == "low":
                steps = [
                    "Identify known values",
                    "Apply formula",
                    "Compute result"
                ]

            elif complexity == "high":
                steps = [
                    "Analyze problem carefully",
                    "Define variables and assumptions",
                    "Select correct laws/formulas",
                    "Derive equations step-by-step",
                    "Solve systematically",
                    "Verify consistency",
                    "Present final answer clearly"
                ]

            else:
                steps = [
                    "Understand problem",
                    "Identify relevant formulas",
                    "Solve step-by-step",
                    "Verify result"
                ]

            return ReasoningEngine._format(steps)

        # -------------------------
        # CODING
        # -------------------------
        if task_type == "coding":

            if complexity == "high":
                steps = [
                    "Analyze requirements deeply",
                    "Design algorithm and data structures",
                    "Consider time and space complexity",
                    "Implement clean modular code",
                    "Test edge cases",
                    "Validate correctness"
                ]
            else:
                steps = [
                    "Understand problem",
                    "Design solution",
                    "Implement code",
                    "Check correctness"
                ]

            return ReasoningEngine._format(steps)

        # -------------------------
        # LOGIC / PROOF / REASONING
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:

            steps = [
                "Understand statement",
                "Break into logical components",
                "Apply step-by-step reasoning",
                "Avoid unjustified assumptions",
                "Conclude rigorously"
            ]

            return ReasoningEngine._format(steps)

        # -------------------------
        # ANALYSIS DOMAIN
        # -------------------------
        if task_type in ["analysis", "history", "literature", "biology"]:

            steps = [
                "Identify key concepts",
                "Structure explanation logically",
                "Explain relationships and causality",
                "Support with facts",
                "Conclude clearly"
            ]

            return ReasoningEngine._format(steps)

        # -------------------------
        # GENERAL FALLBACK
        # -------------------------
        return ReasoningEngine._format([
            "Understand question",
            "Think step-by-step",
            "Provide clear and correct answer"
        ])

    # -------------------------
    # FORMATTER (PROMPT SAFE OUTPUT)
    # -------------------------
    @staticmethod
    def _format(steps: list[str]) -> str:
        if not steps:
            return "1. Understand question"

        return "\n".join(
            f"{i + 1}. {step}"
            for i, step in enumerate(steps)
            if step
        )