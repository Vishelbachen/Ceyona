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

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    importance: float = 0.5  # 0..1
    source: str = "chat"
    tags: List[str] = field(default_factory=list)


# -------------------------
# CONVERSATION CONTEXT
# -------------------------
@dataclass
class ConversationContext:
    user_id: str

    messages: List[ContextMessage] = field(default_factory=list)

    summary: Optional[str] = None
    language: str = "auto"

    emotional_state: Optional[str] = None
    topic: Optional[str] = None

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
        role = (role or "user").lower()
        text = (text or "").strip()

        if not text:
            return

        # clamp importance (SAFETY FIX)
        importance = max(0.0, min(1.0, importance))

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
        return self.messages[-limit:]

    # -------------------------
    # FILTER BY IMPORTANCE
    # -------------------------
    def get_important(self, threshold: float = 0.7) -> List[ContextMessage]:
        if not self.messages:
            return []

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

        lines = []

        for m in chunk:
            if not m.text:
                continue

            role = (m.role or "USER").upper().strip()
            lines.append(f"{role}: {m.text}")

        return "\n".join(lines) if lines else "EMPTY"