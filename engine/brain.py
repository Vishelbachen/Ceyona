import logging

logger = logging.getLogger(__name__)


class Brain:
    """
    Ceyona Expert Brain v2
    Domain-aware reasoning controller
    """

    def analyze(self, text: str, route: dict) -> dict:
        text_lower = text.lower()

        domain = route.get("domain", "general")

        # =========================
        # DOMAIN DETECTION OVERRIDE
        # =========================

        if any(x in text_lower for x in ["prove", "theorem", "f(", "limit", "integral", "derivative"]):
            domain = "math"

        elif any(x in text_lower for x in ["force", "energy", "velocity", "physics"]):
            domain = "physics"

        elif any(x in text_lower for x in ["reaction", "h2o", "chemical", "chemistry"]):
            domain = "chemistry"

        elif any(x in text_lower for x in ["code", "function", "algorithm", "python"]):
            domain = "coding"

        logger.info(f"[Brain] domain={domain}")

        return {
            "domain": domain,
            "mode": self._select_mode(domain),
            "needs_verification": True
        }

    def _select_mode(self, domain: str) -> str:

        if domain == "math":
            return "proof_mode"

        if domain == "physics":
            return "formula_mode"

        if domain == "chemistry":
            return "reaction_mode"

        if domain == "coding":
            return "algorithm_mode"

        return "general_mode"

    def verify(self, response: str, domain: str) -> str:
        """
        Simple self-check layer (v2 lightweight version)
        """

        if not response:
            return "Invalid response"

        # базовая защита от мусора
        if len(response) < 10:
            return "Response too short, recompute needed"

        # можно расширить позже (LLM-as-judge)
        return response