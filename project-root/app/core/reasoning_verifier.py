class ReasoningVerifier:
    """
    Output validation layer (v2.0 stable).

    Goals:
    - reduce false positives
    - context-aware validation
    - safe for production pipeline
    - extensible for self-healing loop (v1.4+)
    """

    # -------------------------
    # NORMALIZATION
    # -------------------------
    @staticmethod
    def _norm(text: str) -> str:
        return (text or "").strip().lower()

    # -------------------------
    # MAIN VERIFY
    # -------------------------
    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:

        issues = []

        task_type = ReasoningVerifier._norm(task_type)
        answer_raw = answer or ""
        answer_clean = answer_raw.strip()

        # -------------------------
        # EMPTY CHECK
        # -------------------------
        if not answer_clean:
            return {
                "is_valid": False,
                "corrected_answer": None,
                "issues": ["empty"]
            }

        # -------------------------
        # LENGTH CHECK (soft signal)
        # -------------------------
        if len(answer_clean) < 20:
            issues.append("too_short")

        # -------------------------
        # MATH / SCIENCE
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            # soft heuristic only (NOT strict)
            has_math_signal = any(sym in answer_clean for sym in ["=", "≈", "+", "-", "∫", "√"])

            if not has_math_signal and len(answer_clean) > 50:
                issues.append("missing_math_signal")

        # -------------------------
        # CODING
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            code_signals = ["def ", "class ", "import ", "return ", "{", "}", "=>"]

            if not any(sig in answer_clean for sig in code_signals):
                issues.append("no_code_signal")

        # -------------------------
        # LOGIC / REASONING (light check only)
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:
            if len(answer_clean) > 200 and "because" not in answer_clean.lower():
                issues.append("weak_reasoning_signal")

        # -------------------------
        # FINAL DECISION
        # -------------------------
        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "corrected_answer": answer_clean if is_valid else None,
            "issues": issues
        }