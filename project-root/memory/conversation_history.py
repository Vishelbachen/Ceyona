class ConversationHistory:
    """
    Stores chat history per user
    """

    def __init__(self):
        self.history = {}

    def add(self, user_id: str, message: str):
        self.history.setdefault(user_id, []).append(message)

    def get(self, user_id: str):
        return self.history.get(user_id, [])