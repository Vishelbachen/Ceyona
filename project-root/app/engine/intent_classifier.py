from app.engine.types import IntentResult


def classify_intent(text: str) -> IntentResult:
    """
    Intent signal generator (NOT a router).

    ONLY purpose:
    - estimate handling style
    - provide confidence signal

    DO NOT:
    - select models
    - override task classifier
    """

    t = (text or "").lower().strip()

    # -------------------------
    # SAFETY SIGNAL
    # -------------------------
    if any(w in t for w in ["bomb", "kill", "weapon", "hack", "attack"]):
        return IntentResult(
            intent="safety",
            complexity="high",
            risk="high",
            confidence=0.9
        )

    # -------------------------
    # REASONING SIGNAL
    # -------------------------
    if any(w in t for w in ["prove", "why", "derive", "solve", "calculate"]):
        return IntentResult(
            intent="reasoning",
            complexity="high",
            risk="low",
            confidence=0.8
        )

    # -------------------------
    # CREATIVE SIGNAL
    # -------------------------
    if any(w in t for w in ["write", "story", "poem", "generate", "compose"]):
        return IntentResult(
            intent="creative",
            complexity="medium",
            risk="low",
            confidence=0.75
        )

    # -------------------------
    # FAST SIGNAL
    # -------------------------
    if len(t) < 60:
        return IntentResult(
            intent="fast",
            complexity="low",
            risk="low",
            confidence=0.6
        )

    # -------------------------
    # DEFAULT CHAT
    # -------------------------
    return IntentResult(
        intent="chat",
        complexity="medium",
        risk="low",
        confidence=0.5
    )