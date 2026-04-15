class Reason:
    def analyze(self, text: str) -> dict:
        text = text or ""

        return {
            "length": len(text),
            "keywords": text.split() if text else []
        }