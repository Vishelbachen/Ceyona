from typing import Any, Dict, Optional


class SentryClient:
    """
    AI Platform v4.7 — Sentry Error Reporter

    RESPONSIBILITY:
    - Capture exceptions
    - Send error events to external monitoring system
    - Provide raw error telemetry

    STRICT RULES:
    - No error interpretation
    - No severity classification logic
    - No retry/fallback decisions
    - No LLM / retrieval / memory usage
    - No orchestration influence
    """

    def __init__(self, dsn: str):
        self.dsn = dsn

    def capture_exception(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Sends exception to Sentry (mock implementation).
        """

        event_id = f"event_{id(error)}"

        # NOTE: real implementation would send to Sentry SDK

        return event_id

    def capture_message(
        self,
        message: str,
        level: str = "error",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Sends a custom message to Sentry.
        """

        event_id = f"msg_{hash(message)}"

        return event_id