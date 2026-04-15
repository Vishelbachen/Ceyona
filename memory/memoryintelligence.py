from memory.cache import MemoryCache


class MemoryIntelligence:
    def __init__(self):
        self.cache = MemoryCache()

    async def retrieve(self, user_id: str, query: str):
        history = await self.cache.get(user_id)

        if not history:
            return ""

        # простая релевантность (заготовка под embeddings)
        relevant = history[-5:]

        return "\n".join(relevant)

    async def store(self, user_id: str, user_input: str, response: str, score: int):
        entry = f"User: {user_input}\nAI: {response}\nScore: {score}"

        await self.cache.append(user_id, entry)