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
    return {"counters": dict(_counters), "gauges": dict(_gauges)}