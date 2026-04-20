from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone


# -------------------------
# USER MESSAGE (COGNITIVE EVENT)
# -------------------------
class UserMessage(BaseModel):
    user_id: str
    text: str

    language: str = "auto"
    task_type: str = "general"

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    source: Literal["telegram", "api", "web", "system"] = "telegram"

    session_id: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

    # -------------------------
    # SAFE NORMALIZATION (IMMUTABLE STYLE)
    # -------------------------
    def normalize(self) -> "UserMessage":
        return UserMessage(
            user_id=self.user_id,
            text=(self.text or "").strip(),
            language=self.language or "auto",
            task_type=self.task_type or "general",
            timestamp=self.timestamp,
            source=self.source,
            session_id=self.session_id,
            metadata=self.metadata or {},
        )


# -------------------------
# ORCHESTRATOR REQUEST
# -------------------------
class OrchestratorRequest(BaseModel):

    trace_id: str
    user_message: UserMessage

    priority: Literal["low", "normal", "high"] = "normal"

    mode: Literal["single", "multi"] = "single"

    preloaded_context: Dict[str, Any] = Field(default_factory=dict)