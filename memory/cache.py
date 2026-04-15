import json
import time


class MemoryCache:
    """
    Simple in-memory cache (can be replaced with Redis later)
    """

    def __init__(self):
        self.store = {}

    def set(self, key: str, value: dict, ttl: int = 300):
        self.store[key] = {
            "value": value,
            "expire": time.time() + ttl
        }

    def get(self, key: str):
        item = self.store.get(key)

        if not item:
            return None

        if time.time() > item["expire"]:
            del self.store[key]
            return None

        return item["value"]