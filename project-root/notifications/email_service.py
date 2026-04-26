from __future__ import annotations

from typing import Dict, Any, Optional

import aiohttp

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# EMAIL SERVICE
# =========================
class EmailService:
    """
    ROLE:
    - send emails via external provider (e.g. Brevo)
    - act as side-effect delivery layer

    STRICT RULES:
    - no decision making
    - no formatting logic for business content
    - no retry policies beyond basic transport safety
    - no state tracking
    """

    BASE_URL = "https://api.brevo.com/v3/smtp/email"

    def __init__(self):
        self.api_key = settings.BREVO_API_KEY

    # =========================
    # SEND EMAIL
    # =========================
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        sender_email: Optional[str] = None,
    ) -> Dict[str, Any]:

        payload = {
            "sender": {
                "email": sender_email or "no-reply@system.local",
            },
            "to": [
                {
                    "email": to_email,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.BASE_URL,
                json=payload,
                headers=headers,
            ) as resp:
                data = await resp.json()

        return self._normalize_response(data)

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:

        return {
            "status": data.get("message"),
            "message_id": data.get("messageId"),
            "raw": data,
        }