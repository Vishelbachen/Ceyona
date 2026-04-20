class AppError(Exception):

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Literal

-------------------------

ERROR SEVERITY LEVELS

-------------------------

Severity = Literal["low", "medium", "high", "critical"]

-------------------------

BASE ERROR (COGNITIVE)

-------------------------

class AppError(Exception):
"""
Cognitive-aware system error.

Used both as:  
- runtime exception  
- structured reasoning signal  
"""  

def __init__(  
    self,  
    code: str,  
    message: str,  
    layer: str,  
    trace_id: Optional[str] = None,  
    severity: Severity = "medium",  
    context: Optional[Dict[str, Any]] = None,  
    recoverable: bool = True,  
    suggestion: Optional[str] = None,  
):  
    super().__init__(message)  

    self.code = code  
    self.message = message  
    self.layer = layer  
    self.trace_id = trace_id  
    self.severity = severity  

    # safe default (CRITICAL FIX)  
    self.context = context or {}  

    self.recoverable = recoverable  
    self.suggestion = suggestion  

# -------------------------  
# SERIALIZATION SAFE OUTPUT  
# -------------------------  
def to_dict(self) -> Dict[str, Any]:  
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
# DEBUG REPRESENTATION  
# -------------------------  
def __str__(self) -> str:  
    return f"[{self.layer}] {self.code}: {self.message}"

-------------------------

ORCHESTRATOR ERRORS

-------------------------

class OrchestratorError(AppError):
pass

-------------------------

LLM ERRORS

-------------------------

class LLMError(AppError):
pass

-------------------------

ROUTER / MODEL ERRORS

-------------------------

class RouterError(AppError):
pass

-------------------------

API / EXTERNAL ERRORS

-------------------------

class APIError(AppError):
pass