import os
import time
from groq import Groq


class ModelRouter:
    def __init__(self):
        self.client = None
        self.cache = None
        self.cache_time = 0
        self.ttl = 300

        self.fast_preferred = "llama-3.1-8b-instant"
        self.smart_preferred = "llama-3.3-70b-versatile"

    def _get_client(self):
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY missing")
            self.client = Groq(api_key=api_key)
        return self.client

    def _refresh(self):
        try:
            res = self._get_client().models.list()
            self.cache = [m.id for m in res.data]
            self.cache_time = time.time()
            return self.cache
        except Exception:
            return self.cache or []

    def models(self):
        if self.cache is None or time.time() - self.cache_time > self.ttl:
            return self._refresh()
        return self.cache

    def _available(self, model):
        return model in self.models()

    def fast(self):
        models = self.models()

        if self._available(self.fast_preferred):
            return self.fast_preferred

        for m in models:
            if "8b" in m or "instant" in m:
                return m

        return models[0] if models else self.fast_preferred

    def smart(self):
        models = self.models()

        if self._available(self.smart_preferred):
            return self.smart_preferred

        for priority in ["70b", "32b", "17b"]:
            for m in models:
                if priority in m:
                    return m

        return self.fast()

    def select(self, mode="fast"):
        return self.smart() if mode == "smart" else self.fast()