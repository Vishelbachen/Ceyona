"""
Log-based span tracing.

Design (architecture.md §10 / audit §10.2):
- Distributed tracing = structured JSON spans via stdlib logging.
- Interface: `with trace(name, **tags)` — stable contract, backend-agnostic.
- trace_id is propagated via contextvars — callers never manage it explicitly.
- Spans are emitted as structured log records readable by fly logs and any
  JSON-aware log aggregator (Datadog, Grafana Loki, etc.).
- No OpenTelemetry collector required. OTLP migration path: replace this
  module's backend only — all call sites remain unchanged.

Span output format:
    {
      "event": "span",
      "span": "<name>",
      "trace_id": "<uuid4-hex>",
      "span_id": "<uuid4-hex[:8]>",
      "parent_id": "<uuid4-hex[:8]> | null",
      "elapsed_ms": <float>,
      "status": "ok" | "error",
      <...tags>
    }

trace_id lifecycle:
- Set once at the outermost span (e.g. handle_message in webhook).
- Inherited by all nested spans in the same async context.
- Reset automatically when the outermost span exits.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator

logger = logging.getLogger(__name__)

# ── context state ─────────────────────────────────────────────────────────────
# Both vars are task-local (asyncio-safe). No manual cleanup needed —
# ContextVar tokens restore previous values on reset().

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id:  ContextVar[str | None] = ContextVar("span_id",  default=None)


def current_trace_id() -> str | None:
    """Return the active trace_id, or None if no span is active."""
    return _trace_id.get()


@contextmanager
def trace(name: str, **tags) -> Generator:
    """
    Emit a structured span covering the duration of the wrapped block.

    Usage (unchanged from previous API):
        with trace("coordinator", tier="general", intent="code"):
            ...

    Nesting: inner spans inherit the outer trace_id and record the
    outer span_id as parent_id.
    """
    # Inherit or create trace_id
    existing_trace = _trace_id.get()
    is_root = existing_trace is None
    trace_id = existing_trace if existing_trace else uuid.uuid4().hex

    # Each span gets its own span_id
    parent_id = _span_id.get()
    span_id   = uuid.uuid4().hex[:8]

    # Set context for this span and any nested spans
    t_token = _trace_id.set(trace_id)
    s_token = _span_id.set(span_id)

    start   = time.perf_counter()
    status  = "ok"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        span_record = {
            "event":      "span",
            "span":       name,
            "trace_id":   trace_id,
            "span_id":    span_id,
            "parent_id":  parent_id,
            "elapsed_ms": elapsed_ms,
            "status":     status,
            **{k: str(v) for k, v in tags.items()},
        }

        logger.info("trace", extra={"span_json": json.dumps(span_record)})

        # Restore previous context
        _trace_id.reset(t_token)
        _span_id.reset(s_token)