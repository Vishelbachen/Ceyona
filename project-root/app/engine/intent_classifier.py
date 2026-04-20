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


# -------------------------
# MAIN CLASSIFIER
# -------------------------
def classify_intent(text: str) -> IntentResult:

    t = (text or "").lower().strip()

    word_count = len(t.split())

    # -------------------------
    # SAFETY (more precise)
    # -------------------------
    safety_keywords = [
        "explosive", "bomb", "weapon system", "terror", "assault",
        "malware", "virus payload"
    ]

    if any(w in t for w in safety_keywords):
        return IntentResult("safety", "high", "high", 0.9)

    # -------------------------
    # REASONING (context-aware)
    # -------------------------
    reasoning_keywords = [
        "prove", "derive", "solve", "calculate", "equation",
        "optimize", "analyze step", "logic", "why does"
    ]

    if any(w in t for w in reasoning_keywords):

        complexity = "high" if word_count > 80 else "medium"

        return IntentResult(
            intent="reasoning",
            complexity=complexity,
            risk="low",
            confidence=0.85
        )

    # -------------------------
    # CREATIVE
    # -------------------------
    creative_keywords = [
        "write", "story", "poem", "generate text", "compose"
    ]

    if any(w in t for w in creative_keywords):
        return IntentResult("creative", "medium", "low", 0.8)

    # -------------------------
    # FAST (not length-based only)
    # -------------------------
    fast_signals = [
        word_count < 15,
        "what is" in t,
        "how to" in t and word_count < 20,
        "translate" in t
    ]

    if any(fast_signals):
        return IntentResult("fast", "low", "low", 0.65)

    # -------------------------
    # DEFAULT CHAT
    # -------------------------
    return IntentResult("chat", "medium", "low", 0.6)