from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agents.fast_agent import FastAgent
from agents.deep_agent import DeepAgent
from agents.creative_agent import CreativeAgent
from agents.safety_agent import SafetyAgent
from agents.consensus_engine import ConsensusEngine

from cognition.intent_engine import IntentResult
from cognition.reasoning_engine import ReasoningResult


@dataclass
class AgentTask:
    agent_name: str
    payload: Dict[str, Any]


@dataclass
class AgentResult:
    agent_name: str
    output: Any
    confidence: float


class MultiAgentCoordinator:
    """
    Orchestrates agent execution layer.

    Responsibilities:
    - distribute tasks to agents
    - collect results
    - forward to consensus engine
    - DO NOT perform reasoning or final decision making
    """

    def __init__(
        self,
        fast_agent: FastAgent,
        deep_agent: DeepAgent,
        creative_agent: CreativeAgent,
        safety_agent: SafetyAgent,
        consensus_engine: ConsensusEngine,
    ):
        self.fast_agent = fast_agent
        self.deep_agent = deep_agent
        self.creative_agent = creative_agent
        self.safety_agent = safety_agent
        self.consensus_engine = consensus_engine

    async def execute(
        self,
        intent: IntentResult,
        reasoning: ReasoningResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main execution entry.

        Input:
            intent - parsed user intent
            reasoning - structured reasoning output
            context - optional memory/retrieval context

        Output:
            consensus result (final agent synthesis)
        """

        context = context or {}

        # =========================
        # 1. TASK DISPATCH
        # =========================
        tasks = self._build_tasks(intent, reasoning, context)

        # =========================
        # 2. PARALLEL EXECUTION
        # =========================
        results: List[AgentResult] = []

        for task in tasks:
            result = await self._execute_agent(task)
            results.append(result)

        # =========================
        # 3. CONSENSUS PHASE
        # =========================
        final_output = await self.consensus_engine.resolve(
            intent=intent,
            reasoning=reasoning,
            agent_results=results,
        )

        return {
            "result": final_output,
            "agent_results": [
                {
                    "agent": r.agent_name,
                    "output": r.output,
                    "confidence": r.confidence,
                }
                for r in results
            ],
        }

    # =========================================================
    # INTERNAL DISPATCH LOGIC
    # =========================================================

    def _build_tasks(
        self,
        intent: IntentResult,
        reasoning: ReasoningResult,
        context: Dict[str, Any],
    ) -> List[AgentTask]:

        tasks: List[AgentTask] = []

        # FAST AGENT — quick structural answer
        tasks.append(
            AgentTask(
                agent_name="fast",
                payload={
                    "intent": intent,
                    "reasoning": reasoning,
                    "context": context,
                },
            )
        )

        # DEEP AGENT — multi-step reasoning
        tasks.append(
            AgentTask(
                agent_name="deep",
                payload={
                    "intent": intent,
                    "reasoning": reasoning,
                    "context": context,
                },
            )
        )

        # CREATIVE AGENT — alternative formulations
        tasks.append(
            AgentTask(
                agent_name="creative",
                payload={
                    "intent": intent,
                    "reasoning": reasoning,
                    "context": context,
                },
            )
        )

        # SAFETY AGENT — validation layer
        tasks.append(
            AgentTask(
                agent_name="safety",
                payload={
                    "intent": intent,
                    "reasoning": reasoning,
                    "context": context,
                },
            )
        )

        return tasks

    # =========================================================
    # EXECUTION ROUTER
    # =========================================================

    async def _execute_agent(self, task: AgentTask) -> AgentResult:
        """
        Routes execution to correct agent.
        """

        if task.agent_name == "fast":
            output = await self.fast_agent.run(task.payload)
            confidence = 0.6

        elif task.agent_name == "deep":
            output = await self.deep_agent.run(task.payload)
            confidence = 0.9

        elif task.agent_name == "creative":
            output = await self.creative_agent.run(task.payload)
            confidence = 0.7

        elif task.agent_name == "safety":
            output = await self.safety_agent.run(task.payload)
            confidence = 1.0  # deterministic guard layer

        else:
            raise ValueError(f"Unknown agent: {task.agent_name}")

        return AgentResult(
            agent_name=task.agent_name,
            output=output,
            confidence=confidence,
        )