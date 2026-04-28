from typing import Any, Dict, Optional, List


class EmailService:
    """
    AI Platform v4.7 — Email Notification Service

    RESPONSIBILITY:
    - Send email messages via external provider
    - Deliver notification payloads
    - Act as transport layer for communication

    STRICT RULES:
    - No business logic
    - No template intelligence
    - No routing decisions
    - No LLM / retrieval / memory usage
    - No orchestrator interaction logic
    """

    def __init__(self, smtp_client: Any):
        self.smtp_client = smtp_client

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a single email.
        """

        # NOTE: In production, this would call SMTP / API provider

        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
            "provider": "mock_smtp",
        }

    async def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Sends email to multiple recipients (no batching logic).
        """

        results = []

        for r in recipients:
            results.append(
                await self.send_email(
                    to=r,
                    subject=subject,
                    body=body,
                )
            )

        return {
            "status": "bulk_sent",
            "count": len(results),
            "results": results,
        }