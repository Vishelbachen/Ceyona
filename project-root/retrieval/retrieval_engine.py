class RetrievalEngine:
    """
    Minimal retrieval layer (no logic yet)
    """

    def search(self, query: str) -> list[str]:
        return [f"dummy_doc_for: {query}"]