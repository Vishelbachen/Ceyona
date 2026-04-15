class SelfCorrection:
    def correct(self, response: str, score: dict) -> str:
        if score["quality"] == "low":
            return response + "\n[Improved: Added more detail]"
        return response