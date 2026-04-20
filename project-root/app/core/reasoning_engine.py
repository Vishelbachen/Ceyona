class ReasoningEngine:
    """
    Unified reasoning strategy layer.
    Not model-specific.
    """

    # 🧠 COMPATIBILITY MAP (fix taxonomy mismatch)
    ALIASES = {
        "math_physics": "math",
        "coding": "algorithm",
        "analysis": "history"
    }

    @staticmethod
    def get_protocol(task_type: str) -> str:

        task_type = ReasoningEngine.ALIASES.get(task_type, task_type)

        if task_type in ["math", "physics", "chemistry"]:
            return (
                "Step 1: Understand the problem\n"
                "Step 2: Identify known laws and formulas\n"
                "Step 3: Build equations step-by-step\n"
                "Step 4: Solve logically\n"
                "Step 5: Final answer clearly stated\n"
            )

        if task_type in ["history", "literature", "biology", "geography"]:
            return (
                "Step 1: Identify key concepts\n"
                "Step 2: Provide structured explanation\n"
                "Step 3: Add supporting facts\n"
                "Step 4: Conclude clearly\n"
            )

        if task_type in ["coding", "algorithm"]:
            return (
                "Step 1: Understand requirements\n"
                "Step 2: Design solution\n"
                "Step 3: Write structured code\n"
                "Step 4: Explain complexity if needed\n"
            )

        return (
            "Step 1: Understand question\n"
            "Step 2: Reason logically\n"
            "Step 3: Answer clearly\n"
        )