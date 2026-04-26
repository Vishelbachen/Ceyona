from dataclasses import dataclass
from typing import Any, Dict, Optional

from llm.llm_router import route_llm


@dataclass
class CreativeAgentInput:
    prompt: str
    context: Optional[Dict[str, Any]] = None
    style_guidance: Optional[str] = None


@dataclass
class CreativeAgentOutput:
    content: str
    model_used: str
    metadata: Dict[str, Any]


class CreativeAgent:
    """
    Creative Agent (exploration / variation layer)

    ROLE:
    - generate alternative formulations
    - explore stylistic diversity
    - produce non-deterministic variations

    DOES NOT:
    - decide correctness
    - perform reasoning validation
    - access memory or retrieval directly
    - influence orchestration
    """

    def __init__(self):
        self.role = "creative"

    async def run(self, input_data: CreativeAgentInput) -> CreativeAgentOutput:

        messages = self._build_prompt(input_data)

        result = await route_llm(
            mode="creative",
            messages=messages
        )

        return CreativeAgentOutput(
            content=result["content"],
            model_used=result.get("model", "unknown"),
            metadata={
                "agent": "creative",
                "style": input_data.style_guidance,
            }
        )

    def _build_prompt(self, input_data: CreativeAgentInput):

        messages = []

        # optional style control layer
        if input_data.style_guidance:
            messages.append({
                "role": "system",
                "content": (
                    "You are a creative transformation engine. "
                    f"Style constraint: {input_data.style_guidance}"
                )
            })

        # core instruction (strict boundary control)
        messages.append({
            "role": "system",
            "content": (
                "Generate alternative expressions or variations. "
                "Do not change meaning. Do not introduce new facts."
            )
        })

        messages.append({
            "role": "user",
            "content": input_data.prompt
        })

        return messages