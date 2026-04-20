# app/engine/reasoning_engine.py

class ReasoningEngine:
    """
    Unified reasoning strategy layer (v2.1 CLEAN).

    Role:
    - defines HOW to solve
    - NOT what user wants
    - NOT model selection
    """

    @staticmethod
    def get_protocol(task_type: str, complexity: str = "medium", language: str = "en") -> str:

        task_type = (task_type or "general").lower()
        complexity = (complexity or "medium").lower()

        # -------------------------
        # SCIENCE / MATH DOMAIN
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            if complexity == "low":
                base = [
                    "Identify known values",
                    "Apply formula",
                    "Compute result"
                ]

            elif complexity == "high":
                base = [
                    "Analyze problem carefully",
                    "Define variables and assumptions",
                    "Select correct laws/formulas",
                    "Derive equations step-by-step",
                    "Solve systematically",
                    "Verify consistency",
                    "Present final answer clearly"
                ]

            else:
                base = [
                    "Understand problem",
                    "Identify relevant formulas",
                    "Solve step-by-step",
                    "Verify result"
                ]

            return "\n".join(f"{i+1}. {step}" for i, step in enumerate(base))

        # -------------------------
        # CODING
        # -------------------------
        if task_type == "coding":

            if complexity == "high":
                base = [
                    "Analyze requirements deeply",
                    "Design algorithm and data structures",
                    "Consider complexity (time/space)",
                    "Implement clean modular code",
                    "Test edge cases",
                    "Validate correctness"
                ]
            else:
                base = [
                    "Understand problem",
                    "Design solution",
                    "Implement code",
                    "Check correctness"
                ]

            return "\n".join(f"{i+1}. {step}" for i, step in enumerate(base))

        # -------------------------
        # REASONING / LOGIC
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:

            return "\n".join([
                "1. Understand statement",
                "2. Break into logical components",
                "3. Apply step-by-step reasoning",
                "4. Avoid unjustified assumptions",
                "5. Conclude rigorously"
            ])

        # -------------------------
        # ANALYSIS
        # -------------------------
        if task_type in ["analysis", "history", "literature", "biology"]:

            return "\n".join([
                "1. Identify key concepts",
                "2. Structure explanation logically",
                "3. Explain relationships and causality",
                "4. Support with facts",
                "5. Conclude clearly"
            ])

        # -------------------------
        # GENERAL
        # -------------------------
        return "\n".join([
            "1. Understand question",
            "2. Think step-by-step",
            "3. Provide clear answer"
        ])