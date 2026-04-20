class ReasoningVerifier:
    """
    Post-processing reasoning verification layer (v2).

    Purpose:
    - detect logical/mathematical inconsistencies
    - validate minimal structural correctness
    - support retry pipeline (future v1.4)
    """

    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:
        issues = []

        if not answer or not answer.strip():
            return {
                "is_valid": False,
                "corrected_answer": None,
                "issues": ["empty_answer"]
            }

        text = answer.strip().lower()

        # 🧠 MATH / PHYSICS
        if task_type in ["math", "physics", "chemistry"]:
            has_result = any(x in answer for x in ["=", "≈", "answer", "result"])
            if not has_result:
                issues.append("missing_result_expression")

        # 🧠 CODING
        if task_type in ["coding", "algorithm"]:
            if "def " not in text and "class " not in text and "return" not in text:
                issues.append("no_code_structure_detected")

        # 🧠 GENERAL QUALITY
        if len(answer) < 20:
            issues.append("too_short_response")

        # 🧠 BASIC CONSISTENCY CHECK
        if "error" in text or "cannot" in text:
            issues.append("failure_indicator_detected")

        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "corrected_answer": answer if is_valid else None,
            "issues": issues
        }