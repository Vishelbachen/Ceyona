class DistributedMemory:
    """
    Simulates distributed memory nodes (Supabase-ready architecture)
    """

    def __init__(self):
        self.nodes = {
            "hot": {},
            "warm": {},
            "cold": {}
        }

    def store(self, user_id: str, data: dict, tier: str = "hot"):
        if user_id not in self.nodes[tier]:
            self.nodes[tier][user_id] = []

        self.nodes[tier][user_id].append(data)

    def retrieve(self, user_id: str):
        return {
            "hot": self.nodes["hot"].get(user_id, []),
            "warm": self.nodes["warm"].get(user_id, []),
            "cold": self.nodes["cold"].get(user_id, [])
        }