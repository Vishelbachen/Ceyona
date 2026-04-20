from dataclasses import dataclass
from typing import Literal


IntentType = Literal[
    "fast",
    "reasoning",
    "creative",
    "safety",
    "chat",
]


@dataclass
class IntentResult:
    intent: IntentType
    complexity: str  # low | medium | high
    risk: str        # low | medium | high
    confidence: float


def classify_intent(text: str) -> IntentResult:
    t = (text or "").lower().strip()

    # -------------------------
    # SAFETY
    # -------------------------
    if any(w in t for w in ["bomb", "kill", "weapon", "hack", "attack"]):
        return IntentResult("safety", "high", "high", 0.95)

    # -------------------------
    # REASONING
    # -------------------------
    if any(w in t for w in ["prove", "why", "derive", "solve", "calculate", "equation"]):
        return IntentResult(
            "reasoning",
            "high" if len(t) > 120 else "medium",
            "low",
            0.85
        )

    # -------------------------
    # CREATIVE
    # -------------------------
    if any(w in t for w in ["write", "story", "poem", "generate", "compose"]):
        return IntentResult("creative", "medium", "low", 0.8)

    # -------------------------
    # FAST
    # -------------------------
    if len(t) < 60:
        return IntentResult("fast", "low", "low", 0.6)

    # -------------------------
    # DEFAULT
    # -------------------------
    return IntentResult("chat", "medium", "low", 0.55)