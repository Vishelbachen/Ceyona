from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from contracts.shared_types import ModelInput, ModelOutput


@dataclass(frozen=True)
class ReasoningContext:
    """
    Immutable reasoning context.
    This is PURE data container.
    """
    input_text: str
    intent: str
    features: Dict[str, Any]
    retrieval_context: Optional[List[Dict[str, Any]]] = None
    memory_context: Optional[List[Dict[str, Any]]] = None
    system_constraints: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ReasoningTrace:
    """
    Debuggable reasoning trace (NO execution meaning).
    """
    steps: List[str]
    confidence: float
    complexity_score: float


class ReasoningEngine:
    """
    Stateless reasoning transformation layer.

    RULES:
    - NO LLM calls
    - NO routing decisions
    - NO side effects
    - ONLY transformation of structured data
    """

    def analyze_complexity(self, context: ReasoningContext) -> float:
        score = 0.0

        # text length contribution
        length = len(context.input_text)
        if length > 2000:
            score += 0.4
        elif length > 500:
            score += 0.2

        # retrieval depth
        if context.retrieval_context:
            score += min(len(context.retrieval_context) * 0.05, 0.3)

        # memory influence
        if context.memory_context:
            score += min(len(context.memory_context) * 0.03, 0.2)

        # intent complexity heuristic
        if context.intent in {"reasoning", "analysis", "multi_step"}:
            score += 0.3

        return min(score, 1.0)

    def derive_reasoning_trace(self, context: ReasoningContext) -> ReasoningTrace:
        steps: List[str] = []

        steps.append("input_parsed")
        steps.append(f"intent={context.intent}")

        complexity = self.analyze_complexity(context)
        steps.append(f"complexity_score={complexity:.3f}")

        if context.retrieval_context:
            steps.append(f"retrieval_items={len(context.retrieval_context)}")

        if context.memory_context:
            steps.append(f"memory_items={len(context.memory_context)}")

        confidence = self._compute_confidence(complexity, context)

        return ReasoningTrace(
            steps=steps,
            confidence=confidence,
            complexity_score=complexity,
        )

    def _compute_confidence(self, complexity: float, context: ReasoningContext) -> float:
        base = 0.85

        # higher complexity → lower confidence
        base -= complexity * 0.3

        # retrieval helps confidence
        if context.retrieval_context:
            base += 0.05

        # memory helps slightly
        if context.memory_context:
            base += 0.03

        return max(0.1, min(base, 0.95))

    def build_reasoning_payload(self, context: ReasoningContext) -> ModelOutput:
        """
        Output is STRUCTURED ONLY.
        No natural language generation.
        """

        trace = self.derive_reasoning_trace(context)

        return ModelOutput(
            data={
                "intent": context.intent,
                "complexity": trace.complexity_score,
                "confidence": trace.confidence,
                "steps": trace.steps,
                "retrieval_size": len(context.retrieval_context or []),
                "memory_size": len(context.memory_context or []),
            }
        )