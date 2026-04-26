from __future__ import annotations

from typing import Dict, Any, Optional, List
import time
import uuid


# =========================
# TRACE SPAN
# =========================
class TraceSpan:
    """
    Represents a single execution span in the system.
    """

    def __init__(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.name = name
        self.parent_id = parent_id

        self.start_time: float = time.time()
        self.end_time: Optional[float] = None

        self.metadata: Dict[str, Any] = {}

    def finish(self) -> None:
        self.end_time = time.time()

    def duration(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time


# =========================
# TRACER
# =========================
class Tracer:
    """
    ROLE:
    - track execution flow across system layers
    - build causal execution graph (DAG-like view)
    - support debugging and observability

    STRICT RULES:
    - no business logic
    - no execution control
    - no decision making
    - no performance optimization logic
    """

    def __init__(self):
        self._spans: Dict[str, TraceSpan] = {}
        self._children: Dict[str, List[str]] = {}

    # =========================
    # START SPAN
    # =========================
    def start_span(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> str:

        span = TraceSpan(name=name, parent_id=parent_id)

        self._spans[span.id] = span

        if parent_id:
            if parent_id not in self._children:
                self._children[parent_id] = []
            self._children[parent_id].append(span.id)

        return span.id

    # =========================
    # END SPAN
    # =========================
    def end_span(self, span_id: str) -> None:

        span = self._spans.get(span_id)
        if not span:
            return

        span.finish()

    # =========================
    # ADD METADATA
    # =========================
    def set_metadata(
        self,
        span_id: str,
        key: str,
        value: Any,
    ) -> None:

        span = self._spans.get(span_id)
        if not span:
            return

        span.metadata[key] = value

    # =========================
    # GET TRACE TREE
    # =========================
    def get_trace(self, root_span_id: str) -> Dict[str, Any]:

        def build(span_id: str) -> Dict[str, Any]:
            span = self._spans[span_id]

            return {
                "id": span.id,
                "name": span.name,
                "duration": span.duration(),
                "metadata": span.metadata,
                "children": [
                    build(child_id)
                    for child_id in self._children.get(span_id, [])
                ],
            }

        return build(root_span_id)

    # =========================
    # EXPORT ALL (DEBUG / OBSERVABILITY)
    # =========================
    def export(self) -> Dict[str, Any]:

        return {
            span_id: {
                "name": span.name,
                "parent_id": span.parent_id,
                "duration": span.duration(),
                "metadata": span.metadata,
            }
            for span_id, span in self._spans.items()
        }