class ReasoningVerifier:
    """
    Verification layer for reasoning outputs.
    
    Role:
    - validate logical structure
    - detect missing steps
    - ensure task compliance
    - flag low-quality reasoning
    """

    @staticmethod
    def verify(task_type: str, response_text: str) -> dict:
        """
        Returns:
        {
            "valid": bool,
            "score": float (0-1),
            "issues": list[str],
            "retry_recommended": bool
        }
        """

        text = (response_text or "").lower()
        issues = []
        score = 1.0

        # -------------------------
        # BASIC QUALITY CHECK
        # -------------------------
        if len(text.strip()) < 20:
            return {
                "valid": False,
                "score": 0.0,
                "issues": ["response_too_short"],
                "retry_recommended": True
            }

        # -------------------------
        # TASK-SPECIFIC CHECKS
        # -------------------------

        if task_type == "math_physics":
            if not any(x in text for x in ["=", "+", "-", "*", "/", "step", "law"]):
                issues.append("missing_math_structure")
                score -= 0.3

            if "final" not in text and "answer" not in text:
                issues.append("missing_final_answer")
                score -= 0.2

        elif task_type == "coding":
            if "def" not in text and "function" not in text and "class" not in text:
                issues.append("missing_code_structure")
                score -= 0.3

            if "edge" not in text:
                issues.append("no_edge_case_check")
                score -= 0.1

        elif task_type == "proof":
            if not any(x in text for x in ["therefore", "thus", "hence", "proves"]):
                issues.append("weak_logical_chain")
                score -= 0.3

        # -------------------------
        # GENERAL QUALITY CHECK
        # -------------------------
        filler_phrases = [
            "i think",
            "maybe",
            "not sure",
            "i guess"
        ]

        if any(p in text for p in filler_phrases):
            issues.append("uncertain_language_detected")
            score -= 0.1

        # -------------------------
        # FINAL SCORE NORMALIZATION
        # -------------------------
        score = max(0.0, min(1.0, score))

        retry_recommended = score < 0.6

        return {
            "valid": score >= 0.6,
            "score": score,
            "issues": issues,
            "retry_recommended": retry_recommended
        }