from memory.cache import MemoryCache
from memory.embeddings import Embeddings
from memory.memorygraph import MemoryGraph
from memory.supabase_client import SupabaseClient


class MemoryIntelligence:
    def __init__(self):
        self.cache = MemoryCache()
        self.embeddings = Embeddings()
        self.graph = MemoryGraph()
        self.db = SupabaseClient()

    async def retrieve(self, user_id: str, query: str):
        # 1. local cache
        history = await self.cache.get(user_id)

        # 2. supabase long-term memory
        db_result = self.db.select(
            "messages",
            {"user_id": user_id}
        )

        db_messages = [
            f"{m['role']}: {m['content']}"
            for m in db_result.data
        ]

        # 3. semantic memory
        query_vec = await self.embeddings.embed(query)
        graph_results = await self.graph.search(query_vec, self.embeddings)

        return "\n".join(history[-5:] + db_messages[-10:] + graph_results)

    async def store(self, user_id: str, user_input: str, response: str, score: int):
        # local
        entry = f"User: {user_input}\nAI: {response}"
        await self.cache.append(user_id, entry)

        # supabase
        self.db.insert("messages", {
            "user_id": user_id,
            "role": "user",
            "content": user_input
        })

        self.db.insert("messages", {
            "user_id": user_id,
            "role": "assistant",
            "content": response,
            "score": score
        })

        # semantic graph
        try:
            vec = await self.embeddings.embed(user_input + response)
            await self.graph.add(user_input + response, vec)
        except:
            pass