from typing import Any, Dict, Optional


class Metrics:
    """
    AI Platform v4.7 — Metrics Collector

    RESPONSIBILITY:
    - Collect numeric system metrics
    - Store counters and gauges
    - Provide raw observability data

    STRICT RULES:
    - No analytics or insights
    - No anomaly detection
    - No LLM / retrieval / memory usage
    - No decision-making
    - No orchestrator influence
    """

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}

    # =========================
    # COUNTERS
    # =========================

    def increment(self, name: str, value: int = 1) -> None:
        """
        Increments a counter metric.
        """

        if name not in self._counters:
            self._counters[name] = 0

        self._counters[name] += value

    def get_counter(self, name: str) -> int:
        """
        Returns counter value.
        """

        return self._counters.get(name, 0)

    # =========================
    # GAUGES
    # =========================

    def set_gauge(self, name: str, value: float) -> None:
        """
        Sets a gauge metric.
        """

        self._gauges[name] = value

    def get_gauge(self, name: str) -> float:
        """
        Returns gauge value.
        """

        return self._gauges.get(name, 0.0)

    # =========================
    # SNAPSHOT
    # =========================

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns full metrics snapshot.
        """

        return {
            "counters": self._counters,
            "gauges": self._gauges,
        }

    def reset(self) -> None:
        """
        Resets all metrics (debug only).
        """

        self._counters = {}
        self._gauges = {}