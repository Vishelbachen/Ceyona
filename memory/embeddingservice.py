class EmbeddingService:
    """
    Converts text → vectors for semantic memory
    """

    def embed(self, text: str):
        return [hash(text) % 1000]  # placeholder embedding