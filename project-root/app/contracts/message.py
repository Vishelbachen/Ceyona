from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone


# -------------------------
# USER MESSAGE (COGNITIVE EVENT)
# -------------------------
class UserMessage(BaseModel):
    user_id: str

    text: str

    # 🧠 cognitive enrichment
    language: Optional[str] = "auto"
    task_type: Optional[str] = "general"  # math | coding | reasoning | chat | analysis

    # timezone-safe timestamp (critical for distributed systems)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 🧠 context metadata
    source: Optional[Literal["telegram", "api", "web", "system"]] = "telegram"

    session_id: Optional[str] = None

    # 🧠 structured metadata (always safe dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # -------------------------
    # SAFE NORMALIZATION HOOK
    # -------------------------
    def normalize(self) -> "UserMessage":
        """
        Ensures pipeline-safe input for:
        - intent_classifier
        - prompt_builder
        - reasoning_engine
        """

        self.text = (self.text or "").strip()

        if not self.task_type:
            self.task_type = "general"

        if not self.metadata:
            self.metadata = {}

        return self


# -------------------------
# ORCHESTRATOR REQUEST (COGNITIVE PACKET)
# -------------------------
class OrchestratorRequest(BaseModel):

    trace_id: str

    user_message: UserMessage

    # 🧠 routing priority
    priority: Optional[Literal["low", "normal", "high"]] = "normal"

    # 🧠 future multi-agent expansion
    mode: Optional[Literal["single", "multi"]] = "single"

    # 🧠 preloaded context (retrieval / memory layer)
    preloaded_context: Dict[str, Any] = Field(default_factory=dict)