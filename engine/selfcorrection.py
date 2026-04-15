class SelfCorrection:
    """
    NO text mutation noise anymore.
    Only optional improvement flag (internal use safe)
    """

    def correct(self, response: str, score: dict) -> str:
        if not response:
            return response

        quality = score.get("quality", "high")

        # ❌ removed: no more appended junk text
        # ❌ removed: "[Improved: ...]"

        if quality == "low" and len(response) < 30:
            return response + "\n\n(Note: answer may be incomplete)"

        return response