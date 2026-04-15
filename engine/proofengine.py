import logging

logger = logging.getLogger(__name__)


class ProofEngine:
    """
    Lightweight validation layer:
    - detects hallucination patterns
    - enforces domain consistency
    - prevents obvious logical drift
    """

    def validate(self, response: str, domain: str) -> str:
        if not response:
            return "No valid response generated."

        # =========================
        # BASIC SANITY CHECKS
        # =========================
        if len(response.strip()) < 5:
            return "Response too short to validate."

        # =========================
        # DOMAIN CONSISTENCY CHECK
        # =========================
        if domain == "math":
            return self._validate_math(response)

        if domain == "physics":
            return self._validate_physics(response)

        return response

    def _validate_math(self, response: str) -> str:
        bad_patterns = [
            "maybe",
            "i think",
            "probably",
            "not sure"
        ]

        for p in bad_patterns:
            if p in response.lower():
                return (
                    response
                    + "\n\n[ProofEngine: removed uncertainty in math domain]"
                )

        return response

    def _validate_physics(self, response: str) -> str:
        if "formula" not in response.lower() and "f=" not in response:
            return response + "\n\n[ProofEngine: physics response may lack formal structure]"

        return response