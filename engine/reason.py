class Reason:
    def analyze(self, text: str) -> dict:
        return {
            "length": len(text),
            "keywords": text.split()
        }