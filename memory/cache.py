class MemoryCache:
    def __init__(self):
        self.storage = {}

    async def get(self, user_id: str):
        return self.storage.get(user_id, [])

    async def append(self, user_id: str, value: str):
        if user_id not in self.storage:
            self.storage[user_id] = []

        self.storage[user_id].append(value)

        # ограничение памяти
        if len(self.storage[user_id]) > 50:
            self.storage[user_id] = self.storage[user_id][-50:]