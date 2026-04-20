from app.core.types import IntentResult


# -------------------------
# MAIN CLASSIFIER
# -------------------------
def classify_intent(text: str) -> IntentResult:

    t = (text or "").lower().strip()
    word_count = len(t.split())

    # -------------------------
    # SAFETY
    # -------------------------
    safety_keywords = [
        "explosive", "bomb", "weapon", "terror",
        "malware", "virus", "attack"
    ]

    if any(k in t for k in safety_keywords):
        return IntentResult(
            intent="safety",
            risk="high",
            complexity="high",
            confidence=0.95,
            task_type="analysis"
        )

    # -------------------------
    # CODING
    # -------------------------
    coding_keywords = [
        "code", "function", "class", "api", "python",
        "bug", "fix", "error", "stack trace"
    ]

    if any(k in t for k in coding_keywords):
        return IntentResult(
            intent="reasoning",
            task_type="coding",
            complexity="high" if word_count > 40 else "medium",
            confidence=0.9
        )

    # -------------------------
    # MATH / PHYSICS
    # -------------------------
    math_keywords = [
        "solve", "equation", "integral", "derivative",
        "force", "velocity", "energy", "calculate"
    ]

    if any(k in t for k in math_keywords):
        return IntentResult(
            intent="reasoning",
            task_type="math_physics",
            complexity="high" if word_count > 60 else "medium",
            confidence=0.9
        )

    # -------------------------
    # CREATIVE
    # -------------------------
    creative_keywords = [
        "story", "poem", "write", "novel", "character"
    ]

    if any(k in t for k in creative_keywords):
        return IntentResult(
            intent="creative",
            task_type="general",
            complexity="medium",
            confidence=0.8
        )

    # -------------------------
    # FAST PATH
    # -------------------------
    if (
        word_count < 12
        or "what is" in t
        or "translate" in t
    ):
        return IntentResult(
            intent="fast",
            task_type="general",
            complexity="low",
            confidence=0.7
        )

    # -------------------------
    # DEFAULT
    # -------------------------
    return IntentResult(
        intent="chat",
        task_type="general",
        complexity="medium",
        confidence=0.6
    )