class UsageMeter:
    """
    Tracks token / request usage for billing
    """

    def __init__(self):
        self.usage = {}

    def add_usage(self, user_id: str, tokens: int):
        self.usage[user_id] = self.usage.get(user_id, 0) + tokens

    def get_usage(self, user_id: str) -> int:
        return self.usage.get(user_id, 0)