class SelfImprove:
    def improve(self, response: str, score: dict) -> str:
        if score["quality"] == "high":
            return response + "\n\n[Ceyona refined output]"
        return response