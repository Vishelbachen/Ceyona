class MemoryGraph:
    """
    Lightweight memory relationships (pseudo-graph AI memory)
    """

    def __init__(self):
        self.graph = {}

    def link(self, user_id: str, key: str, value: str):
        if user_id not in self.graph:
            self.graph[user_id] = []

        self.graph[user_id].append({
            "key": key,
            "value": value
        })

    def get(self, user_id: str):
        return self.graph.get(user_id, [])