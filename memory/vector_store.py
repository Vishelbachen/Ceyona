class VectorStore:
    """
    Real semantic memory layer (production-ready concept)
    """

    def __init__(self):
        self.index = []

    def add(self, vector, metadata):
        self.index.append({
            "vector": vector,
            "metadata": metadata
        })

    def search(self, query_vector, top_k=5):
        # placeholder similarity search
        return self.index[:top_k]