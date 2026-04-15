class MemoryGraph:
    def __init__(self):
        self.nodes = []

    async def add(self, text: str, embedding: list):
        self.nodes.append({
            "text": text,
            "embedding": embedding
        })

        if len(self.nodes) > 200:
            self.nodes = self.nodes[-200:]

    async def search(self, query_embedding, embeddings_model):
        scored = []

        for node in self.nodes:
            sim = embeddings_model.similarity(
                query_embedding,
                node["embedding"]
            )
            scored.append((sim, node["text"]))

        scored.sort(reverse=True)
        return [text for _, text in scored[:5]]