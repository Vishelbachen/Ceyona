import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Brain:
    """
    Ceyona Expert Brain v3
    Lightweight deterministic reasoning classifier + domain router
    """

    def analyze(self, text: str, route: Dict[str, Any]) -> Dict[str, Any]:
        text_l = (text or "").lower()

        domain = self._detect_domain(text_l)
        complexity = self._detect_complexity(text_l)
        intent = route.get("type", "general")

        return {
            "domain": domain,
            "complexity": complexity,
            "intent": intent,
            "mode": self._select_mode(domain, complexity, intent),
        }

    def _detect_domain(self, text: str) -> str:
        # MATH / PHYSICS / CHEM / CODE / GENERAL
        if any(x in text for x in ["solve", "prove", "equation", "f(", "∫", "derivative", "="]):
            return "math"

        if any(x in text for x in ["force", "energy", "velocity", "acceleration", "physics"]):
            return "physics"

        if any(x in text for x in ["reaction", "molecule", "chemistry", "mol"]):
            return "chemistry"

        if any(x in text for x in ["code", "python", "function", "bug", "error"]):
            return "code"

        return "general"

    def _detect_complexity(self, text: str) -> str:
        if len(text) > 300:
            return "high"
        if any(x in text for x in ["prove", "derive", "show that"]):
            return "high"
        return "normal"

    def _select_mode(self, domain: str, complexity: str, intent: str) -> str:
        if domain == "math" and complexity == "high":
            return "math_proof_engine"

        if domain == "physics":
            return "physics_solver"

        if domain == "chemistry":
            return "chem_engine"

        if domain == "code":
            return "code_reasoning"

        return "general_llm"

    def verify(self, response: str, domain: str) -> str:
        """
        lightweight sanity check (NOT rewrite engine)
        """
        if not response:
            return "System error. Empty response."

        if domain == "math" and "?" in response and len(response) < 20:
            return "Mathematical solution incomplete. Please retry."

        return response