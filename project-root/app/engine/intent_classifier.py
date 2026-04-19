from app.engine.types import IntentResult


class IntentClassifier:

    @staticmethod
    def classify(text: str) -> IntentResult:
        text_lower = text.lower()

        # SAFETY
        if any(w in text_lower for w in ["kill", "suicide", "bomb"]):
            return IntentResult("safety", 0.95)

        # REASONING
        if any(w in text_lower for w in ["why", "explain", "how does"]):
            return IntentResult("reasoning", 0.7)

        # CREATIVE
        if any(w in text_lower for w in ["story", "write", "imagine"]):
            return IntentResult("creative", 0.7)

        # FAST
        if len(text) < 40:
            return IntentResult("fast", 0.6)

        return IntentResult("general", 0.5)