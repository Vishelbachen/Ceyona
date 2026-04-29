import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_TIMEOUT = 10.0
_FROM_EMAIL = "noreply@whileshesleeps.ai"
_FROM_NAME = "AI Platform"


class EmailService:
    """
    Sends transactional emails via Brevo API.
    Async. No state. No retry logic (fire-and-forget).
    """

    def __init__(self) -> None:
        self._headers = {
            "api-key": settings.brevo_api_key,
            "Content-Type": "application/json",
        }

    async def send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send a single transactional email."""
        if not settings.brevo_api_key:
            logger.warning("Brevo API key not set, skipping email")
            return False

        payload = {
            "sender": {"name": _FROM_NAME, "email": _FROM_EMAIL},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    _BREVO_URL,
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                logger.info("Email sent", extra={
                    "to": to_email,
                    "subject": subject,
                })
                return True
        except Exception as exc:
            logger.error("Email send failed", extra={
                "to": to_email,
                "error": str(exc),
            })
            return False


# Singleton
email_service = EmailService()