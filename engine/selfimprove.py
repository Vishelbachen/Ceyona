class SelfImprove:
    """
    NO OUTPUT INJECTION VERSION
    Only internal scoring logic allowed
    """

    def improve(self, response: str, score: dict) -> str:
        if not response:
            return response

        # ❌ NEVER modify user-visible output with tags
        # ❌ removed: [Ceyona refined output]

        quality = score.get("quality", "high")

        # safe minimal enhancement only
        if quality == "low" and len(response) < 40:
            return response + "\n\n(Answer may be incomplete)"

        return response