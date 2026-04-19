from dataclasses import dataclass
from typing import Literal


IntentType = Literal[
    "fast",
    "reasoning",
    "creative",
    "safety",
    "general"
]


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float