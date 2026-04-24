import redis
from app.settings import settings

r = redis.from_url(settings.REDIS_URL)

def publish(event: dict):
    r.publish("events", str(event))

def subscribe():
    pubsub = r.pubsub()
    pubsub.subscribe("events")
    return pubsub