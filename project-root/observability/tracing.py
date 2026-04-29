import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Span:
    name: str
    start: float = field(default_factory=time.monotonic)
    tags: dict = field(default_factory=dict)

    def finish(self) -> float:
        elapsed = (time.monotonic() - self.start) * 1000
        logger.info("Span finished", extra={
            "span": self.name,
            "duration_ms": round(elapsed, 2),
            **self.tags,
        })
        return elapsed


@asynccontextmanager
async def trace(name: str, **tags):
    span = Span(name=name, tags=tags)
    try:
        yield span
    finally:
        span.finish()