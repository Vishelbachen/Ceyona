class ReasoningEngine:
    """
    Unified reasoning strategy layer (v2.2 clean + scalable).

    Role:
    - defines HOW to solve
    - language-aware reasoning structure
    - stable prompt injection layer
    """

    # -------------------------
    # NORMALIZATION
    # -------------------------
    @staticmethod
    def _norm(value: str) -> str:
        return (value or "").strip().lower()

    # -------------------------
    # MAIN
    # -------------------------
    @staticmethod
    def get_protocol(task_type: str, complexity: str = "medium", language: str = "en") -> str:

        task_type = ReasoningEngine._norm(task_type) or "general"
        complexity = ReasoningEngine._norm(complexity) or "medium"
        language = ReasoningEngine._norm(language)

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
                    "Consider time/space complexity",
                    "Implement modular code",
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
        # LOGIC / PROOF
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
        # ANALYSIS
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
        # GENERAL
        # -------------------------
        return ReasoningEngine._format([
            "Understand question",
            "Think step-by-step",
            "Provide clear answer"
        ])

    # -------------------------
    # FORMATTER (IMPORTANT FOR PROMPT LAYER)
    # -------------------------
    @staticmethod
    def _format(steps: list[str]) -> str:
        return "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))