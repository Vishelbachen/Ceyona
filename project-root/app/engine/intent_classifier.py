from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str        # fast | reasoning | creative | safety | general
    complexity: str    # low | medium | high
    risk: str          # low | medium | high


def classify_intent(text: str) -> IntentResult:
    t = (text or "").lower().strip()

    # -------------------------
    # 1. SAFETY (HIGHEST PRIORITY)
    # -------------------------
    safety_keywords = (
        "bomb", "kill", "weapon", "explosive",
        "hack", "attack", "steal", "drugs"
    )

    if any(w in t for w in safety_keywords):
        return IntentResult(
            intent="safety",
            complexity="high",
            risk="high"
        )

    # -------------------------
    # 2. REASONING (math / logic / explanation)
    # -------------------------
    reasoning_keywords = (
        "why", "how", "prove", "derive",
        "calculate", "solve", "explain",
        "theorem", "formula", "equation"
    )

    math_indicators = (
        "+", "-", "*", "/", "=", "integral", "derivative"
    )

    if any(w in t for w in reasoning_keywords) or any(m in t for m in math_indicators):
        return IntentResult(
            intent="reasoning",
            complexity="high",
            risk="low"
        )

    # -------------------------
    # 3. CREATIVE (writing / generation)
    # -------------------------
    creative_keywords = (
        "write", "story", "poem", "compose",
        "generate", "script", "dialogue"
    )

    if any(w in t for w in creative_keywords):
        return IntentResult(
            intent="creative",
            complexity="medium",
            risk="low"
        )

    # -------------------------
    # 4. FAST (short + simple queries)
    # -------------------------
    if len(t) < 60:
        return IntentResult(
            intent="fast",
            complexity="low",
            risk="low"
        )

    # -------------------------
    # 5. GENERAL (default stable mode)
    # -------------------------
    return IntentResult(
        intent="general",
        complexity="medium",
        risk="low"
    )