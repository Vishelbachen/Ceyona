from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from llm.model_router import route_llm
from cognition.intent_engine import IntentContext


@dataclass
class DeepAgentInput:
    prompt: str
    context: Optional[Dict[str, Any]] = None
    system_instructions: Optional[str] = None


@dataclass
class DeepAgentOutput:
    content: str
    model_used: str
    metadata: Dict[str, Any]


class DeepAgent:
    """
    Deep reasoning agent (HEAVY / GENERAL LLM layer consumer)

    ROLE:
    - complex reasoning
    - multi-step inference
    - structured synthesis
    - long-context processing

    DOES NOT:
    - decide routing
    - access memory directly
    - call retrieval
    - modify system state
    """

    def __init__(self):
        pass

    async def run(
        self,
        input_data: DeepAgentInput,
        intent: Optional[IntentContext] = None
    ) -> DeepAgentOutput:

        # Build structured prompt (no logic here, only formatting)
        messages = self._build_messages(input_data, intent)

        # Route to LLM layer (ONLY authority layer here)
        result = await route_llm(
            mode="deep",
            messages=messages
        )

        return DeepAgentOutput(
            content=result["content"],
            model_used=result.get("model", "unknown"),
            metadata={
                "agent": "deep_agent",
                "intent_type": intent.type if intent else None
            }
        )

    def _build_messages(
        self,
        input_data: DeepAgentInput,
        intent: Optional[IntentContext]
    ):
        messages = []

        if input_data.system_instructions:
            messages.append({
                "role": "system",
                "content": input_data.system_instructions
            })

        # Intent provides structure, NOT decisions
        if intent:
            messages.append({
                "role": "system",
                "content": f"Intent context: {intent.type} | complexity={intent.complexity}"
            })

        messages.append({
            "role": "user",
            "content": input_data.prompt
        })

        return messages