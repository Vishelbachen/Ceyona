import json
import logging
import os
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


def _extras_of(record: logging.LogRecord) -> dict:
    return {
        k: v
        for k, v in record.__dict__.items()
        if k not in _RESERVED_RECORD_ATTRS and not k.startswith("_")
    }


class ExtraFormatter(logging.Formatter):
    """Standard formatter, plus any `extra={...}` fields rendered as
    `key=value` suffixes so they actually show up in stdout/Space logs.

    Default format. Optimised for a human scrolling live container logs
    (HF Spaces / Fly.io viewers) on a phone — short, no quoting overhead,
    easy to scan line by line."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = _extras_of(record)
        if not extras:
            return base
        rendered = " ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
        return f"{base} | {rendered}"


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Not the default — turn it on with
    LOG_FORMAT=json once there's an actual consumer for it (a log
    aggregator like Loki/Datadog/CloudWatch, or even local `jq` filtering).
    Until then, ExtraFormatter is more readable for manual log-tailing.

    Deliberately stdlib-only (no structlog / python-json-logger): those were
    declared in pyproject.toml but never imported anywhere, and external
    JSON-logging packages have historically broken their import path across
    major versions (e.g. python-json-logger 2.x → 3.x). A ~15-line formatter
    we own outright has no such risk and needs no new dependency."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extras_of(record))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    log_format = os.getenv("LOG_FORMAT", "text").strip().lower()
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = ExtraFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Idempotent: avoid stacking duplicate handlers if setup_logging() is
    # ever called more than once (e.g. test fixtures, hot reload).
    root.handlers.clear()
    root.addHandler(handler)