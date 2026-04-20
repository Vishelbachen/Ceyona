from dataclasses import dataclass
from typing import Literal


IntentType = Literal[
    "fast",
    "reasoning",
    "creative",
    "safety",
    "chat"
]


@dataclass
class IntentResult:
    intent: IntentType
    complexity: str  # low | medium | high
    risk: str        # low | medium | high