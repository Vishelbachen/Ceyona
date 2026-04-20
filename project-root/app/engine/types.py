from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


# -------------------------
# INTENT TYPES
# -------------------------
IntentType = Literal[
    "fast",
    "reasoning",
    "creative",
    "safety",
    "chat"
]


# -------------------------
# TASK TYPES (COGNITIVE ROUTING)
# -------------------------
TaskType = Literal[
    "general",
    "math_physics",
    "coding",
    "reasoning",
    "analysis"
]


# -------------------------
# COMPLEXITY LEVEL
# -------------------------
ComplexityLevel = Literal["low", "medium", "high"]


# -------------------------
# RISK LEVEL
# -------------------------
RiskLevel = Literal["low", "medium", "high"]


# -------------------------
# INTENT RESULT (COGNITION SIGNAL)
# -------------------------
@dataclass
class IntentResult:
    """
    Cognitive routing signal.

    Used by:
    - model_decision
    - prompt_builder
    - reasoning_engine
    - verifier
    """

    intent: IntentType
    complexity: ComplexityLevel = "medium"
    risk: RiskLevel = "low"

    # 🧠 new cognitive fields
    confidence: float = 0.7

    task_type: TaskType = "general"

    # optional reasoning hints
    metadata: Optional[Dict[str, Any]] = None