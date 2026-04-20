class ReasoningVerifier:
    """
    Output validation layer.
    """

    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:
        issues = []

        if not answer or not answer.strip():
            return {
                "is_valid": False,
                "corrected_answer": None,
                "issues": ["empty"]
            }

        t = task_type.lower()

        # MATH / SCIENCE
        if t in ["math", "physics", "chemistry"]:
            if "=" not in answer and "≈" not in answer:
                issues.append("missing_result")

        # CODING
        if t in ["coding", "algorithm"]:
            if "def " not in answer and "class " not in answer:
                issues.append("no_code_structure")

        # GENERAL
        if len(answer) < 20:
            issues.append("too_short")

        return {
            "is_valid": len(issues) == 0,
            "corrected_answer": answer if len(issues) == 0 else None,
            "issues": issues
        }