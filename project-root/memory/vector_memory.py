class VectorMemory:
    """
    Semantic memory layer (vector store abstraction)
    """

    def __init__(self):
        self.vectors = {}

    def add(self, key: str, vector: list[float]):
        self.vectors[key] = vector

    def search(self, query_vector: list[float]) -> list[str]:
        return list(self.vectors.keys())[:5]