from core.execution.orchestrator import Orchestrator


class TelegramMessageRouter:
    """
    Routes Telegram messages into core orchestrator
    """

    def __init__(self):
        self.orchestrator = Orchestrator()

    def route(self, message: dict):
        user_id = message["user_id"]
        text = message["text"]

        return self.orchestrator.handle(user_id, text)