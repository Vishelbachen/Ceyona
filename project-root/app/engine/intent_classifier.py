from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str        # chat | reasoning | fast | creative | safety
    complexity: str    # low | medium | high
    risk: str          # low | medium | high


def classify_intent(text: str) -> IntentResult:
    t = text.lower().strip()

    # 🛡 safety layer (strict priority)
    if any(word in t for word in ["bomb", "kill", "weapon", "hack", "attack"]):
        return IntentResult(
            intent="safety",
            complexity="high",
            risk="high"
        )

    # 🧠 reasoning tasks
    if any(word in t for word in ["why", "how", "explain", "prove", "calculate", "derive"]):
        return IntentResult(
            intent="reasoning",
            complexity="high",
            risk="low"
        )

    # 🎭 creative tasks
    if any(word in t for word in ["write", "story", "poem", "generate", "compose"]):
        return IntentResult(
            intent="creative",
            complexity="medium",
            risk="low"
        )

    # ⚡ fast queries
    if len(t) < 60:
        return IntentResult(
            intent="fast",
            complexity="low",
            risk="low"
        )

    # 💬 default chat
    return IntentResult(
        intent="chat",
        complexity="medium",
        risk="low"
    )