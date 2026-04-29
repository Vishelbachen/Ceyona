import logging
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


@contextmanager
def trace(name: str, **tags) -> Generator:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("trace", extra={"span": name, "elapsed_ms": round(elapsed * 1000, 2), **tags})