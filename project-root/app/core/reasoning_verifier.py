class ReasoningVerifier:
    """
    Output validation layer (v2.0 FIXED).

    Goals:
    - reduce false positives
    - safe heuristic validation (non-strict)
    - stable for self-healing loop
    - compatible with Evaluator + Corrector
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
        # EMPTY CHECK (HARD FAIL)
        # -------------------------
        if not answer_clean:
            return {
                "is_valid": False,
                "corrected_answer": None,
                "issues": ["empty"]
            }

        # -------------------------
        # LENGTH CHECK (SOFT SIGNAL)
        # -------------------------
        if len(answer_clean) < 20:
            issues.append("too_short")

        # -------------------------
        # MATH / SCIENCE DOMAIN
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            # soft heuristic (avoid over-restricting LLM output)
            math_signals = ["=", "≈", "+", "-", "*", "/", "∫", "√"]

            has_signal = any(sym in answer_clean for sym in math_signals)

            if not has_signal and len(answer_clean) > 50:
                issues.append("missing_math_signal")

        # -------------------------
        # CODING / ALGORITHM
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            code_signals = ["def ", "class ", "import ", "return ", "{", "}", "=>"]

            if not any(sig in answer_clean for sig in code_signals):
                issues.append("no_code_signal")

        # -------------------------
        # REASONING / LOGIC
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:

            lower = answer_clean.lower()

            # soft heuristic only (avoid false negatives)
            if len(answer_clean) > 200 and not any(
                w in lower for w in ["because", "therefore", "thus", "hence"]
            ):
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