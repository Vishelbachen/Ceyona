import logging
import sys

# Standard attributes every LogRecord carries. Anything NOT in this set was
# passed via `logger.x("msg", extra={...})` and is genuinely extra context.
#
# ROOT CAUSE (found 2026-06-17): the format string below only ever rendered
# %(message)s. Every `extra={"error": str(exc), "model": model, ...}` call
# across the codebase (hf_client, embedding_cache, retrieval_engine, safety_
# agent, webhook, ...) was silently dropped by logging.basicConfig — the
# fields are attached to the LogRecord object but a plain format string never
# surfaces them. That's why production logs only ever showed a bare
# "ERROR llm.hf_client embed failed" with zero detail, even after embed_raw()
# and str(exc) logging were added upstream: the detail was being produced,
# just never printed. This formatter appends those fields back onto the line.
_RESERVED_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "asctime", "message", "taskName",
}


class ExtraFormatter(logging.Formatter):
    """Standard formatter, plus any `extra={...}` fields rendered as
    `key=value` suffixes so they actually show up in stdout/Space logs."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED_RECORD_ATTRS and not k.startswith("_")
        }
        if not extras:
            return base
        rendered = " ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
        return f"{base} | {rendered}"


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ExtraFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Idempotent: avoid stacking duplicate handlers if setup_logging() is
    # ever called more than once (e.g. test fixtures, hot reload).
    root.handlers.clear()
    root.addHandler(handler)