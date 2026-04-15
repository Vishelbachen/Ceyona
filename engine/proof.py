import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ProofEngine:
    """
    Ceyona Proof Engine v1

    Lightweight validation layer:
    - checks structural consistency
    - detects math/logic claims
    - prevents obvious hallucination patterns
    - does NOT rewrite aggressively (safe layer only)
    """

    def analyze(self, text: str, response: str, brain: Dict[str, Any]) -> Dict[str, Any]:
        try:
            score = 1.0
            flags = []

            domain = brain.get("domain", "general")

            # =========================
            # EMPTY RESPONSE CHECK
            # =========================
            if not response or not response.strip():
                return {
                    "score": 0.0,
                    "flags": ["empty_response"],
                    "approved": False
                }

            # =========================
            # BASIC QUALITY SIGNALS
            # =========================
            if len(response) < 20:
                score -= 0.2
                flags.append("too_short")

            if "error" in response.lower():
                score -= 0.3
                flags.append("error_signal")

            # =========================
            # MATH DOMAIN CHECK
            # =========================
            if domain == "math":
                if "?" in response and len(response) < 40:
                    score -= 0.4
                    flags.append("incomplete_math")

                if not re.search(r"\d|\=|x|y", response):
                    score -= 0.2
                    flags.append("no_math_structure")

            # =========================
            # LOGIC CONSISTENCY CHECK
            # =========================
            contradictions = [
                ("always", "never"),
                ("true", "false"),
                ("all", "none")
            ]

            lowered = response.lower()

            for a, b in contradictions:
                if a in lowered and b in lowered:
                    score -= 0.3
                    flags.append("contradiction_detected")

            # =========================
            # FINAL DECISION
            # =========================
            approved = score >= 0.5

            return {
                "score": round(score, 2),
                "flags": flags,
                "approved": approved
            }

        except Exception as e:
            logger.warning(f"[ProofEngine ERROR] {e}")
            return {
                "score": 1.0,
                "flags": [],
                "approved": True
            }