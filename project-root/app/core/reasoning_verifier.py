class ReasoningVerifier:
    """
    Post-generation reasoning validation layer.
    Ensures structural correctness of answers.
    """

    @staticmethod
    def verify(task_type: str, response: str) -> dict:
        issues = []

        if not response or not response.strip():
            return {
                "valid": False,
                "issues": ["empty_response"]
            }

        text = response.lower()

        # 🧠 math/physics structure check
        if task_type in ["math", "physics", "chemistry", "math_physics"]:
            if not any(x in text for x in ["step", "=", "solution"]):
                issues.append("missing_mathematical_structure")

        # 💻 coding validation
        if task_type in ["coding", "algorithm"]:
            if "def " not in response and "class " not in response:
                issues.append("no_code_detected")

        # 📏 too short / too weak reasoning
        if len(response) < 20:
            issues.append("too_short")

        # 📦 overly long garbage protection
        if len(response) > 20000:
            issues.append("too_long")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }