import time


class RateLimiter:
    """
    Simple in-memory rate limiter
    """

    def __init__(self):
        self.requests = {}

    def allow(self, user_id: str, limit: int = 10) -> bool:
        now = time.time()
        timestamps = self.requests.get(user_id, [])

        timestamps = [t for t in timestamps if now - t < 60]
        if len(timestamps) >= limit:
            return False

        timestamps.append(now)
        self.requests[user_id] = timestamps
        return True