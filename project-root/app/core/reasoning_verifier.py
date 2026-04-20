class ReasoningVerifier:
    """
    Post-generation reasoning validation layer.
    Lightweight quality gate for LLM outputs.

    Goals:
    - detect empty / broken outputs
    - check structural integrity
    - avoid false positives
    - remain non-blocking for production flow
    """

    @staticmethod
    def verify(task_type: str, response: str) -> dict:
        issues = []

        # 🧯 EMPTY CHECK (CRITICAL)
        if not response or not response.strip():
            return {
                "valid": False,
                "issues": ["empty_response"]
            }

        text = response.strip()
        lowered = text.lower()

        # 📏 BASIC QUALITY GATES
        if len(text) < 15:
            issues.append("too_short")

        if len(text) > 20000:
            issues.append("too_long")

        # 🧠 MATHEMATICS / PHYSICS CHECK
        if task_type in ["math", "physics", "chemistry", "math_physics"]:
            has_structure = any(
                marker in lowered for marker in [
                    "step", "solution", "answer", "=", "given", "we have"
                ]
            )

            if not has_structure:
                issues.append("missing_reasoning_structure")

        # 💻 CODING CHECK
        if task_type in ["coding", "algorithm"]:
            has_code = any(
                marker in text for marker in [
                    "def ", "class ", "return", "import", "{", "}"
                ]
            )

            if not has_code:
                issues.append("no_code_detected")

        # 📚 GENERAL QUALITY CHECK
        # avoids garbage / meaningless outputs
        low_quality_signals = [
            "???",
            "....",
            "i don't know",
            "no idea"
        ]

        if any(sig in lowered for sig in low_quality_signals):
            issues.append("low_quality_signal_detected")

        # 🧠 FINAL DECISION
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }