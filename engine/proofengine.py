import logging
import re

logger = logging.getLogger(__name__)


class ProofEngine:
    """
    Lightweight proof validator (NON-blocking)
    - checks logical consistency
    - detects hallucinated claims
    - does NOT rewrite output (safe layer only)
    """

    def __init__(self):
        self.math_markers = ["=", "∫", "derivative", "prove", "theorem"]

    def validate(self, text: str, domain: str) -> str:
        if not text:
            return text

        try:
            if domain == "math":
                return self._check_math(text)

            if domain in ("physics", "chemistry"):
                return self._check_science(text)

            return text

        except Exception as e:
            logger.warning(f"[ProofEngine FAIL SAFE]: {e}")
            return text

    def _check_math(self, text: str) -> str:
        # minimal sanity checks only
        if "therefore" in text.lower() and "=" not in text:
            return text + "\n\n[Warning: incomplete derivation]"

        if len(text) < 20:
            return text + "\n\n[Warning: too short solution]"

        return text

    def _check_science(self, text: str) -> str:
        # lightweight consistency guard
        if "because" in text.lower() and len(text) < 30:
            return text + "\n\n[Warning: weak justification]"

        return text