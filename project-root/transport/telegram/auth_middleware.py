class TelegramAuthMiddleware:
    """
    Validates incoming Telegram requests
    """

    def is_valid(self, request: dict) -> bool:
        return "update_id" in request