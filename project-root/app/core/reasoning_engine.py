class ReasoningEngine:
    """
    Unified reasoning strategy layer.
    Not model-specific.
    """

    @staticmethod
    def get_protocol(task_type: str) -> str:

        if task_type in ["math", "physics", "chemistry"]:
            return (
                "Step 1: Carefully interpret the problem and define all variables\n"
                "Step 2: Identify relevant physical/mathematical laws\n"
                "Step 3: Translate the problem into equations\n"
                "Step 4: Solve step-by-step with justification\n"
                "Step 5: Verify result for consistency\n"
                "Step 6: Present final answer clearly\n"
            )

        if task_type in ["history", "literature", "biology", "geography"]:
            return (
                "Step 1: Identify core concepts and context\n"
                "Step 2: Structure the explanation logically\n"
                "Step 3: Support with key facts or examples\n"
                "Step 4: Show relationships and causality\n"
                "Step 5: Conclude clearly\n"
            )

        if task_type in ["coding", "algorithm"]:
            return (
                "Step 1: Understand requirements and constraints\n"
                "Step 2: Choose appropriate algorithm/data structures\n"
                "Step 3: Design clean solution architecture\n"
                "Step 4: Implement correct and readable code\n"
                "Step 5: Analyze complexity and edge cases\n"
            )

        return (
            "Step 1: Understand the question deeply\n"
            "Step 2: Identify key constraints or concepts\n"
            "Step 3: Apply logical reasoning step-by-step\n"
            "Step 4: Ensure answer is consistent and complete\n"
        )