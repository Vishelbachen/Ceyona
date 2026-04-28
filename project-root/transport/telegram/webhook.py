class TelegramWebhook:
    """
    Entry point for Telegram updates (HTTP webhook)
    """

    def handle_update(self, update: dict):
        print(f"[TELEGRAM WEBHOOK] received update: {update}")