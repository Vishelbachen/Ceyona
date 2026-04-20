class ReasoningVerifier:
    """
    Post-processing reasoning verification layer.

    PURPOSE:
    - validate logical correctness
    - detect structural issues
    - enforce answer quality gate
    - support optional regeneration (future)
    """

    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:
        """
        Returns structured validation result
        """

        if not answer or not answer.strip():
            return {
                "is_valid": False,
                "issues": ["empty_answer"],
                "severity": "critical",
                "suggested_action": "regenerate"
            }

        issues = []

        # -------------------------
        # MATH / PHYSICS DOMAIN
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            if not any(op in answer for op in ["=", "≈", "<", ">"]):
                issues.append("missing_formal_result")

            if "error" in answer.lower():
                issues.append("contains_error_marker")

        # -------------------------
        # CODING DOMAIN
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            if "def " not in answer and "class " not in answer:
                issues.append("no_code_structure")

        # -------------------------
        # GENERAL QUALITY
        # -------------------------
        if len(answer) < 20:
            issues.append("too_short")

        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "issues": issues,
            "severity": "low" if is_valid else "medium",
            "suggested_action": None if is_valid else "review"
        }