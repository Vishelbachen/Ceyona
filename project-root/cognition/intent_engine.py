from dataclasses import dataclass
from typing import Dict, Any, Literal


IntentType = Literal[
    "chat",
    "question",
    "task",
    "code",
    "retrieval",
    "system",
]


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    metadata: Dict[str, Any]


# =========================
# 🧠 INTENT ENGINE
# =========================
class IntentEngine:
    """
    Stateless intent classification layer.

    RULES:
    - NO memory access
    - NO LLM routing
    - NO business logic
    - ONLY classification + structuring
    """

    def __init__(self):
        pass

    # =========================
    # 🚀 MAIN ENTRY
    # =========================
    def classify(self, message: str, context: Dict[str, Any] | None = None) -> IntentResult:

        text = message.lower().strip()

        # =========================
        # 🧩 SYSTEM INTENT
        # =========================
        if any(cmd in text for cmd in ["/start", "/help", "/reset"]):
            return IntentResult(
                intent="system",
                confidence=0.99,
                metadata={"type": "command"},
            )

        # =========================
        # 💻 CODE INTENT
        # =========================
        if "```" in text or "def " in text or "class " in text:
            return IntentResult(
                intent="code",
                confidence=0.85,
                metadata={"type": "code_block"},
            )

        # =========================
        # 🔍 RETRIEVAL INTENT
        # =========================
        if any(word in text for word in ["find", "search", "look up", "what is", "who is"]):
            return IntentResult(
                intent="retrieval",
                confidence=0.75,
                metadata={"type": "knowledge_query"},
            )

        # =========================
        # ❓ QUESTION INTENT
        # =========================
        if "?" in text:
            return IntentResult(
                intent="question",
                confidence=0.7,
                metadata={"type": "interrogative"},
            )

        # =========================
        # 🧩 TASK INTENT
        # =========================
        if any(word in text for word in ["create", "build", "make", "generate", "write"]):
            return IntentResult(
                intent="task",
                confidence=0.7,
                metadata={"type": "action_request"},
            )

        # =========================
        # 💬 DEFAULT CHAT
        # =========================
        return IntentResult(
            intent="chat",
            confidence=0.6,
            metadata={"type": "freeform"},
        )