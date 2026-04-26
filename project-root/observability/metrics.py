from __future__ import annotations

from typing import Dict, Any
from dataclasses import dataclass, field
import time


# =========================
# METRIC SNAPSHOT
# =========================
@dataclass
class MetricSnapshot:
    value: float = 0.0
    count: int = 0
    last_updated: float = field(default_factory=lambda: time.time())


# =========================
# METRICS COLLECTOR
# =========================
class Metrics:
    """
    ROLE:
    - collect lightweight numeric telemetry
    - provide runtime visibility into system behavior
    - support observability layer (not decision layer)

    STRICT RULES:
    - no business logic
    - no alerting
    - no interpretation
    - no feedback into execution flow
    """

    def __init__(self):
        self._metrics: Dict[str, MetricSnapshot] = {}

    # =========================
    # INCREMENT COUNTER
    # =========================
    def inc(self, name: str, value: float = 1.0) -> None:

        metric = self._get(name)
        metric.value += value
        metric.count += 1
        metric.last_updated = time.time()

    # =========================
    # SET GAUGE
    # =========================
    def set(self, name: str, value: float) -> None:

        metric = self._get(name)
        metric.value = value
        metric.last_updated = time.time()

    # =========================
    # GET METRIC
    # =========================
    def get(self, name: str) -> Dict[str, Any]:

        metric = self._get(name)

        return {
            "value": metric.value,
            "count": metric.count,
            "last_updated": metric.last_updated,
        }

    # =========================
    # INTERNAL
    # =========================
    def _get(self, name: str) -> MetricSnapshot:

        if name not in self._metrics:
            self._metrics[name] = MetricSnapshot()

        return self._metrics[name]

    # =========================
    # EXPORT ALL
    # =========================
    def export(self) -> Dict[str, Dict[str, Any]]:

        return {
            name: {
                "value": m.value,
                "count": m.count,
                "last_updated": m.last_updated,
            }
            for name, m in self._metrics.items()
        }