import logging

from notifications.email_service import email_service

logger = logging.getLogger(__name__)


class EventNotifier:
    """
    Async side-effects only.
    No business logic. No control flow influence.
    Fires notifications for system events.
    """

    # ── balance events ───────────────────────────────────

    async def on_balance_credited(
        self,
        user_id: int,
        amount_usd: float,
        new_balance_usd: float,
        to_email: str | None = None,
        to_name: str = "User",
    ) -> None:
        logger.info("Event: balance_credited", extra={
            "user_id": user_id,
            "amount_usd": amount_usd,
            "new_balance_usd": new_balance_usd,
        })
        if to_email:
            await email_service.send(
                to_email=to_email,
                to_name=to_name,
                subject="✅ Balance topped up",
                html_content=(
                    f"<p>Hi {to_name},</p>"
                    f"<p>Your balance has been topped up by "
                    f"<strong>${amount_usd:.2f}</strong>.</p>"
                    f"<p>Current balance: <strong>${new_balance_usd:.2f}</strong></p>"
                ),
            )

    async def on_balance_exhausted(
        self,
        user_id: int,
        to_email: str | None = None,
        to_name: str = "User",
    ) -> None:
        logger.warning("Event: balance_exhausted", extra={"user_id": user_id})
        if to_email:
            await email_service.send(
                to_email=to_email,
                to_name=to_name,
                subject="⚠️ Balance exhausted",
                html_content=(
                    f"<p>Hi {to_name},</p>"
                    f"<p>Your balance has run out. "
                    f"Please top up to continue using the service.</p>"
                ),
            )

    # ── safety events ────────────────────────────────────

    async def on_safety_block(
        self,
        user_id: int,
        reason: str,
    ) -> None:
        logger.warning("Event: safety_block", extra={
            "user_id": user_id,
            "reason": reason,
        })

    # ── transport events ─────────────────────────────────

    async def on_send_to_telegram_failed(
        self,
        chat_id: int | None,
        path: str,
        attempts: int,
        error: str,
    ) -> None:
        """
        Fired when every retry of an outbound Telegram call (via the
        Cloudflare Worker proxy) is exhausted — the user never got their
        reply. Logged at ERROR, which Sentry's logging integration picks up
        automatically (see observability/sentry.py) — that is the single
        alerting channel for this event. No separate email path: Sentry
        already has its own delivery-failure alert configured, and a second
        Brevo email would just be the same signal duplicated.
        """
        logger.error("Event: send_to_telegram_failed", extra={
            "chat_id": chat_id,
            "path": path,
            "attempts": attempts,
            "error": error,
        })

    # ── system events ────────────────────────────────────

    async def on_system_error(
        self,
        error: str,
        context: dict | None = None,
    ) -> None:
        logger.error("Event: system_error", extra={
            "error": error,
            "context": context or {},
        })


# Singleton
event_notifier = EventNotifier()