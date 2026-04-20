from dataclasses import dataclass
from typing import Optional, Any, Dict, Literal


# -------------------------
# ERROR SEVERITY LEVELS
# -------------------------
Severity = Literal["low", "medium", "high", "critical"]


# -------------------------
# BASE ERROR (COGNITIVE)
# -------------------------
@dataclass
class AppError(Exception):
    """
    Cognitive-aware system error.

    This is not just a failure signal —
    it is a reasoning input for self-healing systems.
    """

    code: str
    message: str
    layer: str

    trace_id: Optional[str] = None

    # 🧠 new cognitive fields
    severity: Severity = "medium"

    # 🧠 machine-readable context (structured, not free-form chaos)
    context: Optional[Dict[str, Any]] = None

    # 🧠 recovery hint for orchestrator
    recoverable: bool = True

    # 🧠 suggested action for orchestrator
    suggestion: Optional[str] = None

    def to_dict(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "layer": self.layer,
                "trace_id": self.trace_id,
                "severity": self.severity,
                "recoverable": self.recoverable,
                "suggestion": self.suggestion,
                "context": self.context,
            }
        }


# -------------------------
# ORCHESTRATOR ERRORS
# -------------------------
class OrchestratorError(AppError):
    pass


# -------------------------
# LLM ERRORS
# -------------------------
class LLMError(AppError):
    pass


# -------------------------
# ROUTER / MODEL ERRORS
# -------------------------
class RouterError(AppError):
    pass


# -------------------------
# API / EXTERNAL ERRORS
# -------------------------
class APIError(AppError):
    pass