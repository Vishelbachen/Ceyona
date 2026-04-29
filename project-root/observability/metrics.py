from dataclasses import dataclass, field
from collections import defaultdict
import time


@dataclass
class Metrics:
    request_count: int = 0
    error_count: int = 0
    total_cost_usd: float = 0.0
    tier_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies: list[float] = field(default_factory=list)

    def record_request(self, tier: str, cost_usd: float, latency_ms: float) -> None:
        self.request_count += 1
        self.total_cost_usd += cost_usd
        self.tier_counts[tier] += 1
        self.latencies.append(latency_ms)

    def record_error(self) -> None:
        self.error_count += 1

    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    def summary(self) -> dict:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_latency_ms": round(self.avg_latency_ms(), 2),
            "tier_counts": dict(self.tier_counts),
        }


# Singleton
metrics = Metrics()