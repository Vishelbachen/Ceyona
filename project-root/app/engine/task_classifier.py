class TaskClassifier:

    @staticmethod
    def classify(text: str) -> str:
        t = text.lower()

        if any(x in t for x in ["integral", "derivative", "force", "energy"]):
            return "physics"

        if any(x in t for x in ["code", "function", "bug", "algorithm"]):
            return "coding"

        if any(x in t for x in ["who", "when", "where", "history"]):
            return "history"

        if any(x in t for x in ["dna", "cell", "biology"]):
            return "biology"

        return "general"