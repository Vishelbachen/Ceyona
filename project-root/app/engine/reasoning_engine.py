class ReasoningVerifier:
    """
    Output validation layer (v3.0 PRODUCTION).

    Features:
    - soft + hard validation separation
    - severity-aware issues
    - non-blocking by default
    - compatible with self-healing loop
    """

    @staticmethod
    def _norm(text: str) -> str:
        return (text or "").strip().lower()

    @staticmethod
    def verify(task_type: str, question: str, answer: str) -> dict:

        task_type = ReasoningVerifier._norm(task_type)
        answer_raw = answer or ""
        answer_clean = answer_raw.strip()

        issues = []

        # -------------------------
        # HARD CHECKS
        # -------------------------
        if not answer_clean:
            return {
                "is_valid": False,
                "severity": "critical",
                "issues": [{"type": "empty", "severity": "critical"}],
                "corrected_answer": None
            }

        # -------------------------
        # SOFT CHECKS
        # -------------------------

        # LENGTH
        if len(answer_clean) < 20:
            issues.append({"type": "too_short", "severity": "low"})

        # -------------------------
        # MATH / SCIENCE
        # -------------------------
        if task_type in ["math", "physics", "chemistry"]:

            math_signals = ["=", "≈", "+", "-", "*", "/", "∫", "√"]

            has_signal = any(sym in answer_clean for sym in math_signals)

            if not has_signal and len(answer_clean) > 50:
                issues.append({
                    "type": "missing_math_signal",
                    "severity": "medium"
                })

        # -------------------------
        # CODING
        # -------------------------
        if task_type in ["coding", "algorithm"]:

            code_signals = ["def ", "class ", "import ", "return ", "{", "}", "=>"]

            if not any(sig in answer_clean for sig in code_signals):
                issues.append({
                    "type": "no_code_signal",
                    "severity": "medium"
                })

        # -------------------------
        # REASONING
        # -------------------------
        if task_type in ["reasoning", "proof", "logic"]:

            lower = answer_clean.lower()

            if len(answer_clean) > 200 and not any(
                w in lower for w in ["because", "therefore", "thus", "hence"]
            ):
                issues.append({
                    "type": "weak_reasoning_signal",
                    "severity": "low"
                })

        # -------------------------
        # DECISION LOGIC
        # -------------------------
        critical = any(i["severity"] == "critical" for i in issues)
        medium = any(i["severity"] == "medium" for i in issues)

        is_valid = not critical and not medium

        return {
            "is_valid": is_valid,
            "severity": (
                "critical" if critical else
                "medium" if medium else
                "low"
            ),
            "issues": issues,
            "corrected_answer": answer_clean if is_valid else None
        }