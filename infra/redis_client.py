import redis.asyncio as redis


class RedisClient:
    def __init__(self, url="redis://localhost:6379"):
        self.client = redis.from_url(url, decode_responses=True)

    async def set(self, key, value):
        await self.client.set(key, value)

    async def get(self, key):
        return await self.client.get(key)

    async def publish(self, channel, message):
        await self.client.publish(channel, message)

    async def subscribe(self, channel):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub