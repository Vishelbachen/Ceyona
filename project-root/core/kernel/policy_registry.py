from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class PolicyRule:
    """
    Immutable execution policy rule definition.
    """
    name: str
    description: str
    max_tokens: int
    allow_code_execution: bool
    allow_retrieval: bool
    allow_memory: bool
    recommended_agents: list[str]


class PolicyRegistry:
    """
    AI Platform v4.7 — Policy Registry

    RESPONSIBILITY:
    - Store predefined execution policies
    - Provide lookup for EPK / Orchestrator
    - Act as immutable rule catalog

    STRICT RULES:
    - No decision-making
    - No cost calculations
    - No runtime evaluation
    - No LLM / retrieval / memory access
    """

    def __init__(self):
        self._policies: Dict[str, PolicyRule] = {
            "FAST": PolicyRule(
                name="FAST",
                description="Low latency simple reasoning",
                max_tokens=300,
                allow_code_execution=False,
                allow_retrieval=False,
                allow_memory=True,
                recommended_agents=["fast"],
            ),
            "GENERAL": PolicyRule(
                name="GENERAL",
                description="Balanced reasoning and tool usage",
                max_tokens=1200,
                allow_code_execution=True,
                allow_retrieval=True,
                allow_memory=True,
                recommended_agents=["deep", "fast"],
            ),
            "HEAVY": PolicyRule(
                name="HEAVY",
                description="Deep reasoning, long context, complex tasks",
                max_tokens=3000,
                allow_code_execution=True,
                allow_retrieval=True,
                allow_memory=True,
                recommended_agents=["deep", "creative"],
            ),
        }

    def get(self, tier: str) -> Optional[PolicyRule]:
        """
        Retrieve immutable policy definition.
        """
        return self._policies.get(tier)

    def list_policies(self) -> Dict[str, PolicyRule]:
        """
        Returns full policy catalog (read-only usage expected).
        """
        return self._policies