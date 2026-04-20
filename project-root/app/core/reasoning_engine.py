class ReasoningEngine:
    """
    Unified reasoning strategy layer (v2).

    Improvements:
    - aligned with intent system
    - adaptive reasoning depth
    - reduced duplication with prompt_builder
    - scalable reasoning templates
    """

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    @staticmethod
    def get_protocol(task_type: str, complexity: str = "medium") -> str:

        task_type = (task_type or "general").lower()
        complexity = (complexity or "medium").lower()

        # -------------------------
        # MATH / PHYSICS / SCIENCE
        # -------------------------
        if task_type in ["math_physics", "math", "physics", "chemistry"]:

            if complexity == "low":
                return (
                    "1. Identify known values\n"
                    "2. Apply formula\n"
                    "3. Compute result\n"
                )

            if complexity == "high":
                return (
                    "1. Carefully analyze problem statement\n"
                    "2. Define variables and assumptions\n"
                    "3. Select appropriate physical/mathematical laws\n"
                    "4. Derive equations step-by-step\n"
                    "5. Solve systematically\n"
                    "6. Verify dimensional and logical consistency\n"
                    "7. Present final result clearly\n"
                )

            return (
                "1. Understand problem\n"
                "2. Identify relevant formulas\n"
                "3. Solve step-by-step\n"
                "4. Check result\n"
            )

        # -------------------------
        # CODING / ALGORITHMS
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            if complexity == "high":
                return (
                    "1. Analyze requirements deeply\n"
                    "2. Design algorithm and data structures\n"
                    "3. Consider time and space complexity\n"
                    "4. Implement clean, modular code\n"
                    "5. Test edge cases\n"
                    "6. Validate correctness\n"
                )

            return (
                "1. Understand problem\n"
                "2. Design solution\n"
                "3. Implement code\n"
                "4. Check correctness\n"
            )

        # -------------------------
        # LOGICAL REASONING / PROOF
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:

            return (
                "1. Understand statement\n"
                "2. Break into logical components\n"
                "3. Apply step-by-step reasoning\n"
                "4. Avoid assumptions without justification\n"
                "5. Conclude rigorously\n"
            )

        # -------------------------
        # ANALYSIS / GENERAL EXPLANATION
        # -------------------------
        if task_type in ["analysis", "history", "literature", "biology"]:

            return (
                "1. Identify key concepts\n"
                "2. Organize structure logically\n"
                "3. Explain relationships and causality\n"
                "4. Support with relevant facts\n"
                "5. Provide clear conclusion\n"
            )

        # -------------------------
        # GENERAL FALLBACK
        # -------------------------
        return (
            "1. Understand question\n"
            "2. Think step-by-step\n"
            "3. Provide clear answer\n"
        )