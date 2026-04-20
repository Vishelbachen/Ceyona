from app.engine.types import IntentResult


def classify_intent(text: str) -> IntentResult:
    """
    Task-level heuristic classifier.

    IMPORTANT:
    This is NOT final routing logic.
    Only early signal extraction.
    """

    t = (text or "").lower().strip()

    # -------------------------
    # SAFETY / HIGH RISK
    # -------------------------
    if any(w in t for w in [
        "bomb", "kill", "weapon", "hack", "attack", "explosive"
    ]):
        return IntentResult(
            intent="safety",
            complexity="high",
            risk="high",
            confidence=0.9
        )

    # -------------------------
    # REASONING / MATH / SCIENCE
    # -------------------------
    if any(w in t for w in [
        "prove", "why", "how", "derive",
        "solve", "calculate", "equation", "integral"
    ]):
        return IntentResult(
            intent="reasoning",
            complexity="high" if len(t) > 100 else "medium",
            risk="low",
            confidence=0.8
        )

    # -------------------------
    # CREATIVE TASKS
    # -------------------------
    if any(w in t for w in [
        "write", "story", "poem", "generate", "compose"
    ]):
        return IntentResult(
            intent="creative",
            complexity="medium",
            risk="low",
            confidence=0.75
        )

    # -------------------------
    # FAST / SIMPLE
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