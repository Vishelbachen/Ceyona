from __future__ import annotations

from typing import Optional, Dict, Any

try:
    import sentry_sdk
except ImportError:  # optional dependency
    sentry_sdk = None


# =========================
# SENTRY CLIENT
# =========================
class SentryClient:
    """
    ROLE:
    - forward errors and context to Sentry (if enabled)

    STRICT RULES:
    - no business logic
    - no dependency on Sentry availability
    - no failure propagation (must be safe)
    """

    def __init__(self, dsn: Optional[str] = None):
        self._enabled = bool(dsn and sentry_sdk)
        self._dsn = dsn

        if self._enabled:
            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=0.0,  # tracing handled separately
            )

    # =========================
    # CAPTURE EXCEPTION
    # =========================
    def capture_exception(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:

        if not self._enabled:
            return

        try:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for k, v in context.items():
                        scope.set_extra(k, v)

                sentry_sdk.capture_exception(error)

        except Exception:
            # never break system due to observability
            pass

    # =========================
    # CAPTURE MESSAGE
    # =========================
    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:

        if not self._enabled:
            return

        try:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for k, v in context.items():
                        scope.set_extra(k, v)

                sentry_sdk.capture_message(message, level=level)

        except Exception:
            pass

    # =========================
    # SET USER (OPTIONAL)
    # =========================
    def set_user(self, user_id: str) -> None:

        if not self._enabled:
            return

        try:
            sentry_sdk.set_user({"id": user_id})
        except Exception:
            pass

    # =========================
    # CLEAR USER
    # =========================
    def clear_user(self) -> None:

        if not self._enabled:
            return

        try:
            sentry_sdk.set_user(None)
        except Exception:
            pass