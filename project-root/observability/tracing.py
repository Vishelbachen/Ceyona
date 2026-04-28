from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class Tracer:
    """
    AI Platform v4.7 — Tracing System

    RESPONSIBILITY:
    - Track request execution flow across system layers
    - Create trace spans for debugging and observability
    - Maintain causal chain of execution steps

    STRICT RULES:
    - No performance analysis
    - No anomaly detection
    - No LLM / retrieval / memory usage
    - No decision-making
    - No orchestration influence
    """

    def __init__(self):
        self._traces: Dict[str, List[Dict[str, Any]]] = {}

    def start_trace(self, request_id: Optional[str] = None) -> str:
        """
        Creates a new trace session.
        """

        trace_id = request_id or str(uuid.uuid4())
        self._traces[trace_id] = []

        return trace_id

    def add_span(
        self,
        trace_id: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Adds a span (execution step) to trace.
        """

        if trace_id not in self._traces:
            self._traces[trace_id] = []

        span = {
            "operation": operation,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._traces[trace_id].append(span)

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Returns full trace for request.
        """

        return self._traces.get(trace_id, [])

    def clear_trace(self, trace_id: str) -> None:
        """
        Deletes trace data.
        """

        if trace_id in self._traces:
            del self._traces[trace_id]