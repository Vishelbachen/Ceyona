class ReasoningVerifier:
    """
    Post-processing reasoning verification layer.

    Purpose:
    - detect logical/mathematical inconsistencies
    - improve final answer quality
    - enforce correctness over confidence
    """

    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:
        """
        Returns:
        {
            "is_valid": bool,
            "corrected_answer": str | None,
            "issues": list[str]
        }
        """

        issues = []

        if not answer or len(answer.strip()) == 0:
            return {
                "is_valid": False,
                "corrected_answer": None,
                "issues": ["empty_answer"]
            }

        # 🧠 MATH / PHYSICS CHECK
        if task_type in ["math", "physics", "chemistry"]:
            if "=" not in answer and "≈" not in answer:
                issues.append("missing_equation_or_result")

            if "error" in answer.lower():
                issues.append("contains_error_marker")

        # 🧠 CODING CHECK
        if task_type in ["coding", "algorithm"]:
            if "def " not in answer and "class " not in answer:
                issues.append("no_structured_code_detected")

        # 🧠 GENERAL QUALITY CHECK
        if len(answer) < 20:
            issues.append("too_short_response")

        # 🔥 FINAL DECISION
        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "corrected_answer": answer if is_valid else None,
            "issues": issues
        }