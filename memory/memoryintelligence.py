from memory.cache import MemoryCache
from memory.embeddings import Embeddings
from memory.memorygraph import MemoryGraph


class MemoryIntelligence:
    def __init__(self):
        self.cache = MemoryCache()
        self.embeddings = Embeddings()
        self.graph = MemoryGraph()

    async def retrieve(self, user_id: str, query: str):
        history = await self.cache.get(user_id)

        if not history:
            return ""

        query_vec = await self.embeddings.embed(query)

        graph_results = await self.graph.search(query_vec, self.embeddings)

        recent = history[-5:]

        return "\n".join(recent + graph_results)

    async def store(self, user_id: str, user_input: str, response: str, score: int):
        entry = f"User: {user_input}\nAI: {response}\nScore: {score}"

        await self.cache.append(user_id, entry)

        combined = f"{user_input} {response}"

        try:
            vec = await self.embeddings.embed(combined)
            await self.graph.add(combined, vec)
        except Exception:
            pass