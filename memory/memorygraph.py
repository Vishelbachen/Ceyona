import datetime


class MemoryGraph:
    def __init__(self, db, embeddings):
        self.db = db
        self.embeddings = embeddings

    async def store_interaction(self, user_id: str, text: str, response: str):
        vector = await self.embeddings.embed(text)

        data = {
            "user_id": user_id,
            "text": text,
            "response": response,
            "embedding": vector,
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        self.db.insert("memory", data)

    def get_recent(self, user_id: str, limit: int = 5):
        result = self.db.select(
            "memory",
            filters={"user_id": user_id},
            limit=limit
        )

        return result.data if result else []

    def semantic_search(self, embedding: list, user_id: str):
        result = self.db.rpc(
            "match_memory",
            {
                "query_embedding": embedding,
                "match_user": user_id,
                "match_threshold": 0.75,
                "match_count": 5
            }
        )

        return result.data if result else []