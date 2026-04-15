import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Brain:
    """
    Ceyona Brain v4 (Stable Production Version)
    - deterministic routing
    - no output mutation
    - safe classification only
    """

    def analyze(self, text: str, route: Dict[str, Any]) -> Dict[str, Any]:
        text_l = (text or "").lower()

        return {
            "domain": self._detect_domain(text_l),
            "complexity": self._detect_complexity(text_l),
            "intent": route.get("type", "general") if route else "general",
            "mode": self._select_mode(text_l, route),
        }

    def _detect_domain(self, text: str) -> str:
        if any(x in text for x in ["solve", "prove", "equation", "derivative", "integral"]):
            return "math"

        if any(x in text for x in ["force", "energy", "velocity", "acceleration"]):
            return "physics"

        if any(x in text for x in ["reaction", "molecule", "chem", "mol"]):
            return "chemistry"

        if any(x in text for x in ["code", "python", "bug", "error", "function"]):
            return "code"

        return "general"

    def _detect_complexity(self, text: str) -> str:
        if len(text) > 350:
            return "high"

        if any(x in text for x in ["prove", "derive", "explain step"]):
            return "high"

        return "normal"

    def _select_mode(self, text: str, route: Dict[str, Any]) -> str:
        if "math" in text:
            return "math_solver"

        if "code" in text:
            return "code_engine"

        return "general_llm"

    def verify(self, response: str, domain: str) -> str:
        if not response or not isinstance(response, str):
            return "System error. Empty response."

        # ONLY safety check, no rewriting
        if domain == "math" and len(response) < 15:
            return "Incomplete solution. Please retry."

        return response