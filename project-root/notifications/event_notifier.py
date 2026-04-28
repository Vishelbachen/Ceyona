from typing import Any, Dict, List, Optional


class EventNotifier:
    """
    AI Platform v4.7 — Event Notifier

    RESPONSIBILITY:
    - Dispatch system events to external notification channels
    - Bridge event system and notification services
    - Route already-decided events to delivery mechanisms

    STRICT RULES:
    - No event interpretation
    - No business logic
    - No decision-making
    - No LLM / retrieval / memory usage
    - No orchestrator influence
    """

    def __init__(
        self,
        email_service: Any,
        webhook_client: Optional[Any] = None,
    ):
        self.email_service = email_service
        self.webhook_client = webhook_client

    async def notify(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches a single event to appropriate channels.
        """

        event_type = event.get("type")
        payload = event.get("payload", {})

        results = {
            "event_type": event_type,
            "delivered_to": [],
        }

        # =========================
        # EMAIL CHANNEL
        # =========================
        if event.get("channels", {}).get("email"):
            await self.email_service.send_email(
                to=payload.get("email"),
                subject=payload.get("subject", "Notification"),
                body=payload.get("body", ""),
            )
            results["delivered_to"].append("email")

        # =========================
        # WEBHOOK CHANNEL
        # =========================
        if self.webhook_client and event.get("channels", {}).get("webhook"):
            await self.webhook_client.post(
                url=payload.get("webhook_url"),
                payload=payload,
            )
            results["delivered_to"].append("webhook")

        return results

    async def notify_bulk(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes multiple events sequentially (no batching intelligence).
        """

        results = []

        for event in events:
            results.append(await self.notify(event))

        return results