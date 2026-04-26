from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from llm.llm_router import route_llm


SafetyDecision = Literal["ALLOW", "DENY", "DEGRADED"]


@dataclass
class SafetyInput:
    prompt: str
    context: Optional[Dict[str, Any]] = None
    intent: Optional[Dict[str, Any]] = None


@dataclass
class SafetyOutput:
    decision: SafetyDecision
    confidence: float
    reason: str
    metadata: Dict[str, Any]


class SafetyAgent:
    """
    Safety Agent (policy enforcement layer)

    ROLE:
    - classify risk level
    - enforce deterministic safety policy
    - block / degrade / allow execution

    DOES NOT:
    - generate answers
    - perform reasoning
    - influence content generation
    - access memory/retrieval
    """

    def __init__(self):
        self.role = "safety"

    async def run(self, input_data: SafetyInput) -> SafetyOutput:

        # =========================
        # 1. FAST SAFETY CHECK (LLM CLASSIFIER)
        # =========================
        result = await route_llm(
            mode="safety",
            messages=self._build_messages(input_data)
        )

        decision, confidence, reason = self._parse(result)

        return SafetyOutput(
            decision=decision,
            confidence=confidence,
            reason=reason,
            metadata={
                "agent": "safety",
                "raw_model_output": result,
            }
        )

    # =========================
    # PROMPT BUILDER
    # =========================
    def _build_messages(self, input_data: SafetyInput):

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a deterministic safety classification system.\n"
                    "Classify the request into one of:\n"
                    "- ALLOW: safe to proceed\n"
                    "- DENY: unsafe, must be blocked\n"
                    "- DEGRADED: allowed but must reduce capabilities\n\n"
                    "Return strict JSON:\n"
                    "{ decision: str, confidence: float, reason: str }"
                )
            },
            {
                "role": "user",
                "content": input_data.prompt
            }
        ]

        return messages

    # =========================
    # PARSING LAYER (STRICT)
    # =========================
    def _parse(self, result: Any):

        try:
            data = result["content"]

            # expected structured output
            decision = data.get("decision", "DEGRADED")
            confidence = float(data.get("confidence", 0.5))
            reason = data.get("reason", "no reason provided")

            # enforce hard constraints
            if decision not in ("ALLOW", "DENY", "DEGRADED"):
                decision = "DEGRADED"

            return decision, confidence, reason

        except Exception:
            # fail-safe default
            return "DEGRADED", 0.3, "parsing_error"