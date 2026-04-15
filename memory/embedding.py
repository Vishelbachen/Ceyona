class EmbeddingEngine:
    def embed(self, text: str):
        return hash(text) % 10000