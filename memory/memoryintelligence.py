class MemoryIntelligence:
    def __init__(self, memory_graph, embeddings):
        self.memory = memory_graph
        self.embeddings = embeddings

    async def build_context(self, user_id: str, text: str) -> dict:
        """
        Собирает умный контекст:
        - recent messages
        - semantic memory
        """

        query_embedding = await self.embeddings.embed(text)

        recent = self.memory.get_recent(user_id)
        semantic = self.memory.semantic_search(query_embedding, user_id)

        return {
            "recent": recent,
            "semantic": semantic
        }

    async def update_memory(self, user_id: str, text: str, response: str):
        await self.memory.store_interaction(user_id, text, response)