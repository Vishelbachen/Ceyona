class MemoryIntelligence:
    def __init__(self):
        self.storage = {}

    async def retrieve(self, user_id: str, query: str):
        return self.storage.get(user_id, "")

    async def store(self, user_id: str, user_input: str, response: str, score: int):
        history = self.storage.get(user_id, "")
        new_entry = f"\nUser: {user_input}\nAI: {response}"
        self.storage[user_id] = history + new_entry