import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProofEngine:
    """
    PRO MAX Proof Engine (Unified Layer)

    Combines:
    - evaluation (score + flags)
    - validation (domain consistency)
    - optional response stabilization
    """

    def analyze(self, text: str, response: str, brain: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not response:
                return self._fail("empty_response")

            score = 1.0
            flags = []

            domain = (brain or {}).get("domain", "general")
            lowered = response.lower()

            # =========================
            # BASIC QUALITY CHECKS
            # =========================
            if len(response.strip()) < 20:
                score -= 0.25
                flags.append("too_short")

            if any(x in lowered for x in ["error", "exception", "traceback"]):
                score -= 0.35
                flags.append("runtime_error_signal")

            # =========================
            # CONTRADICTION DETECTION
            # =========================
            contradictions = [
                ("always", "never"),
                ("all", "none"),
                ("true", "false"),
                ("can", "cannot")
            ]

            for a, b in contradictions:
                if a in lowered and b in lowered:
                    score -= 0.3
                    flags.append("logical_contradiction")

            # =========================
            # DOMAIN: MATH
            # =========================
            if domain == "math":
                if not re.search(r"\d|=|x|y", response):
                    score -= 0.25
                    flags.append("missing_math_structure")

                if any(x in lowered for x in ["maybe", "probably", "i think", "not sure"]):
                    score -= 0.2
                    flags.append("uncertainty_in_math")

            # =========================
            # DOMAIN: PHYSICS
            # =========================
            if domain == "physics":
                if "formula" not in lowered and "f=" not in lowered and "=" not in response:
                    score -= 0.2
                    flags.append("missing_physics_structure")

            # =========================
            # FINAL DECISION
            # =========================
            approved = score >= 0.5

            return {
                "score": round(score, 2),
                "flags": flags,
                "approved": approved,
                "domain": domain
            }

        except Exception as e:
            logger.warning(f"[ProofEngine ERROR] {e}")
            return self._fail("internal_error")

    # =========================================================
    # OPTIONAL: RESPONSE SANITIZER (SAFE FIX MODE)
    # =========================================================
    def sanitize(self, response: str, brain: Dict[str, Any]) -> str:
        """
        Light correction layer (NOT rewriting aggressively)
        """
        if not response:
            return response

        domain = (brain or {}).get("domain", "general")

        # remove weak uncertainty in strict domains
        if domain in ["math", "physics"]:
            response = re.sub(r"\b(maybe|probably|i think|not sure)\b", "", response, flags=re.I)

        # cleanup excessive whitespace
        response = re.sub(r"\n{3,}", "\n\n", response).strip()

        return response

    # =========================================================
    # INTERNAL FAILSAFE
    # =========================================================
    def _fail(self, reason: str) -> Dict[str, Any]:
        return {
            "score": 0.0,
            "flags": [reason],
            "approved": False,
            "domain": "general"
        }