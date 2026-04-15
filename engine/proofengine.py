import logging

logger = logging.getLogger(__name__)


class ProofEngine:
    """
    Safe verification layer (non-blocking)
    Does NOT modify logic, only annotates weak outputs.
    """

    def validate(self, text: str, domain: str) -> str:
        if not text:
            return text

        try:
            if domain == "math":
                return self._math_check(text)

            if domain in ("physics", "chemistry"):
                return self._science_check(text)

            return text

        except Exception as e:
            logger.warning(f"[ProofEngine FAIL SAFE] {e}")
            return text

    def _math_check(self, text: str) -> str:
        t = text.lower()

        if "therefore" in t and "=" not in t:
            return text + "\n\n[Proof Warning: missing formal derivation]"

        if len(text) < 25:
            return text + "\n\n[Proof Warning: incomplete solution]"

        return text

    def _science_check(self, text: str) -> str:
        if "because" in text.lower() and len(text) < 30:
            return text + "\n\n[Proof Warning: weak justification]"

        return text