import re
from typing import Dict, Any


class Brain:
    """
    Ceyona Expert Brain v3
    - domain routing
    - reasoning enhancer
    - structured prompt augmentation
    """

    def __init__(self):
        self.math_keywords = ["solve", "equation", "prove", "function", "integral", "derivative", "f(", "lim"]
        self.physics_keywords = ["force", "energy", "velocity", "acceleration", "newton", "pressure"]
        self.chemistry_keywords = ["reaction", "molecule", "compound", "acid", "base", "molar"]
        self.code_keywords = ["code", "python", "bug", "function", "class", "error", "debug"]

    def detect_domain(self, text: str) -> str:
        t = text.lower()

        if any(k in t for k in self.math_keywords):
            return "math"

        if any(k in t for k in self.physics_keywords):
            return "physics"

        if any(k in t for k in self.chemistry_keywords):
            return "chemistry"

        if any(k in t for k in self.code_keywords):
            return "coding"

        return "general"

    def enhance_reasoning(self, text: str, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        domain = self.detect_domain(text)

        enhanced = dict(reasoning or {})
        enhanced["domain"] = domain

        enhanced["instructions"] = self._get_domain_instructions(domain)

        return enhanced

    def _get_domain_instructions(self, domain: str) -> str:
        if domain == "math":
            return (
                "Solve step-by-step. "
                "Show derivation clearly. "
                "Verify final answer."
            )

        if domain == "physics":
            return (
                "Use physical laws explicitly. "
                "Define variables. "
                "Check units consistency."
            )

        if domain == "chemistry":
            return (
                "Balance reactions if needed. "
                "Explain mechanism logically."
            )

        if domain == "coding":
            return (
                "Explain logic. Provide correct code. "
                "Check edge cases."
            )

        return "Be clear, structured and correct."

    def build_brain_context(self, text: str, context: Dict[str, Any], reasoning: Dict[str, Any]) -> Dict[str, Any]:
        domain = self.detect_domain(text)

        return {
            "domain": domain,
            "context": context,
            "reasoning": self.enhance_reasoning(text, reasoning),
            "mode": f"ceyona_brain_v3::{domain}"
        }