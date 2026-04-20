from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


# -------------------------
# USER MESSAGE (COGNITIVE EVENT)
# -------------------------
class UserMessage(BaseModel):
    user_id: str

    text: str

    # 🧠 cognitive enrichment
    language: Optional[str] = "auto"
    task_type: Optional[str] = "general"  # math | coding | reasoning | chat | analysis

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # 🧠 context metadata (structured instead of raw dict abuse)
    source: Optional[Literal["telegram", "api", "web", "system"]] = "telegram"

    session_id: Optional[str] = None

    # 🧠 optional structured hints from frontend or upstream
    metadata: Optional[Dict[str, Any]] = None


# -------------------------
# ORCHESTRATOR REQUEST (COGNITIVE PACKET)
# -------------------------
class OrchestratorRequest(BaseModel):
    trace_id: str

    user_message: UserMessage

    # 🧠 system-level routing hints
    priority: Optional[Literal["low", "normal", "high"]] = "normal"

    # 🧠 future multi-agent support
    mode: Optional[Literal["single", "multi"]] = "single"

    # 🧠 optional precomputed context (future retrieval layer)
    preloaded_context: Optional[Dict[str, Any]] = None