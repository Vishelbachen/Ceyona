"""
In-memory observability layer.

Design constraints (architecture.md §7 / audit §7.3 / §10.1):
- Metrics are in-memory, per-process, and reset on restart.
- No persistence layer is used by design — metrics are ephemeral signals.
- Data is not aggregated across workers or instances.
- snapshot() is the sole export boundary; consumed by GET /metrics.
- Prometheus / StatsD export is a separate future task (external adapter,
  no changes to this module required).
"""
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

_counters: dict[str, int] = defaultdict(int)
_gauges: dict[str, float] = {}


def increment(name: str, value: int = 1) -> None:
    _counters[name] += value


def gauge(name: str, value: float) -> None:
    _gauges[name] = value


def snapshot() -> dict:
    """
    Return a point-in-time snapshot of all counters and gauges.
    In-process only — not aggregated across workers or instances.
    """
    return {"counters": dict(_counters), "gauges": dict(_gauges)}