class VectorMemory:
    """
    Semantic memory layer (upgrade from simple storage)
    """

    def __init__(self):
        self.store = {}

    def add(self, user_id: str, embedding: list, data: str):
        if user_id not in self.store:
            self.store[user_id] = []

        self.store[user_id].append({
            "embedding": embedding,
            "data": data
        })

    def search(self, user_id: str, query_embedding: list):
        memories = self.store.get(user_id, [])
        return memories[:5]  # placeholder similarity search