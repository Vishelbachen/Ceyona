from dataclasses import dataclass
from typing import Any, Dict, Optional

from llm.llm_router import LLMRouter


@dataclass
class FastAgentInput:
    prompt: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class FastAgentOutput:
    content: str
    model_used: str
    confidence: float
    metadata: Dict[str, Any]


class FastAgent:
    """
    FAST AGENT:
    - low latency inference
    - shallow reasoning only
    - no planning / no decomposition
    """

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        self.role = "fast"

    async def run(self, input_data: FastAgentInput) -> FastAgentOutput:
        """
        Execute fast inference path.
        """

        response = await self.llm_router.route(
            role="fast",
            prompt=input_data.prompt,
            context=input_data.context or {},
        )

        return FastAgentOutput(
            content=response.content,
            model_used=response.model,
            confidence=self._estimate_confidence(response),
            metadata={
                "agent": "fast",
                "latency_class": "low",
            },
        )

    def _estimate_confidence(self, response: Any) -> float:
        """
        Lightweight heuristic confidence estimator.
        No external dependencies.
        """

        if not response or not getattr(response, "content", None):
            return 0.0

        length = len(response.content)

        # simple heuristic (fast-path safe)
        if length < 20:
            return 0.45
        if length < 200:
            return 0.7
        return 0.85