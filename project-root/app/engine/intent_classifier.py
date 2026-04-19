# app/engine/intent_classifier.py

from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str        # chat | reasoning | fast | creative | safety
    complexity: str    # low | medium | high
    risk: str          # low | medium | high


def classify_intent(text: str) -> IntentResult:
    t = text.lower()

    # 🛡 safety layer
    if any(word in t for word in ["bomb", "kill", "hack", "weapon"]):
        return IntentResult(
            intent="safety",
            complexity="high",
            risk="high"
        )

    # 🧠 reasoning (math, physics, explanation)
    if any(word in t for word in ["why", "how", "explain", "prove", "calculate"]):
        return IntentResult(
            intent="reasoning",
            complexity="high",
            risk="low"
        )

    # 🎭 creative
    if any(word in t for word in ["write", "story", "poem", "generate"]):
        return IntentResult(
            intent="creative",
            complexity="medium",
            risk="low"
        )

    # ⚡ fast chat
    if len(text) < 60:
        return IntentResult(
            intent="fast",
            complexity="low",
            risk="low"
        )

    return IntentResult(
        intent="chat",
        complexity="medium",
        risk="low"
    )