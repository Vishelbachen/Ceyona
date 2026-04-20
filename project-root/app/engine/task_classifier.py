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
    complexity: str
    risk: str


def classify_intent(text: str) -> IntentResult:
    t = (text or "").lower().strip()

    # SAFETY
    if any(w in t for w in ["bomb", "kill", "weapon", "hack", "attack"]):
        return IntentResult("safety", "high", "high")

    # REASONING
    if any(w in t for w in ["prove", "why", "how", "derive", "solve", "calculate"]):
        return IntentResult("reasoning", "high", "low")

    # CREATIVE
    if any(w in t for w in ["write", "story", "poem", "generate", "compose"]):
        return IntentResult("creative", "medium", "low")

    # FAST
    if len(t) < 60:
        return IntentResult("fast", "low", "low")

    return IntentResult("chat", "medium", "low")