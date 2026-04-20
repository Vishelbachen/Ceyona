from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


# -------------------------
# CORE ROUTING TYPES
# -------------------------
IntentType = Literal[
    "fast",
    "reasoning",
    "creative",
    "safety",
    "chat"
]

TaskType = Literal[
    "general",
    "math_physics",
    "coding",
    "reasoning",
    "analysis"
]

ComplexityLevel = Literal["low", "medium", "high"]
RiskLevel = Literal["low", "medium", "high"]


# -------------------------
# INTENT RESULT (SINGLE SOURCE OF TRUTH)
# -------------------------
@dataclass
class IntentResult:
    """
    Unified cognitive routing signal.

    This is the CENTRAL object used across:
    - intent_classifier
    - model_decision
    - prompt_builder
    - orchestrator
    - verifier
    """

    intent: IntentType
    complexity: ComplexityLevel = "medium"
    risk: RiskLevel = "low"

    confidence: float = 0.7

    task_type: TaskType = "general"

    # optional debugging / future cognition
    metadata: Optional[Dict[str, Any]] = None

    # -------------------------
    # HELPERS (IMPORTANT FOR SCALE)
    # -------------------------
    def is_high_risk(self) -> bool:
        return self.risk == "high"

    def is_reasoning_task(self) -> bool:
        return self.intent == "reasoning"

    def is_fast_path(self) -> bool:
        return self.intent == "fast"