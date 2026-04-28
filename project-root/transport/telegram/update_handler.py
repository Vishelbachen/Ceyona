class UpdateHandler:
    """
    Parses Telegram updates into internal format
    """

    def parse(self, update: dict) -> dict:
        return {
            "user_id": update.get("user", {}).get("id"),
            "text": update.get("message", {}).get("text", "")
        }