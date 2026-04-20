from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone


# -------------------------
# SINGLE MESSAGE UNIT
# -------------------------
@dataclass
class ContextMessage:
    role: str  # "user" | "assistant" | "system"
    text: str

    # timezone-safe timestamp (IMPORTANT for scaling/logging)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 🧠 cognitive metadata
    importance: float = 0.5  # 0..1
    source: str = "chat"     # chat | memory | retrieval | tool
    tags: List[str] = field(default_factory=list)


# -------------------------
# CONVERSATION CONTEXT
# -------------------------
@dataclass
class ConversationContext:
    user_id: str

    messages: List[ContextMessage] = field(default_factory=list)

    # 🧠 cognitive state
    summary: Optional[str] = None
    language: str = "auto"

    # 🧠 memory intelligence hooks
    emotional_state: Optional[str] = None
    topic: Optional[str] = None

    # 🧠 scoring
    relevance_score: float = 1.0

    # -------------------------
    # ADD MESSAGE
    # -------------------------
    def add_message(
        self,
        role: str,
        text: str,
        importance: float = 0.5,
        source: str = "chat",
        tags: Optional[List[str]] = None
    ):
        self.messages.append(
            ContextMessage(
                role=role,
                text=text,
                importance=importance,
                source=source,
                tags=tags or []
            )
        )

    # -------------------------
    # GET RECENT CONTEXT
    # -------------------------
    def get_recent(self, limit: int = 10) -> List[ContextMessage]:
        return self.messages[-limit:] if self.messages else []

    # -------------------------
    # FILTER BY IMPORTANCE
    # -------------------------
    def get_important(self, threshold: float = 0.7) -> List[ContextMessage]:
        return [
            m for m in self.messages
            if m.importance >= threshold
        ]

    # -------------------------
    # SAFE PROMPT EXPORT
    # -------------------------
    def to_prompt_text(self, limit: int = 10) -> str:
        if not self.messages:
            return "EMPTY"

        chunk = self.get_recent(limit)

        if not chunk:
            return "EMPTY"

        return "\n".join(
            f"{m.role.upper()}: {m.text}"
            for m in chunk
            if m.text
        ) or "EMPTY"