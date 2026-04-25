from fastapi.responses import JSONResponse
import redis
from app.settings import settings

r = redis.from_url(settings.REDIS_URL)

def init_rate_limiter(app):

    @app.middleware("http")
    async def limit_requests(request, call_next):

        try:
            ip = request.client.host
            key = f"rl:{ip}"

            count = r.incr(key)
            r.expire(key, 60)

            if count > 60:
                return JSONResponse({"error": "rate_limited"}, status_code=429)

        except Exception:
            # ❗ NEVER BREAK REQUEST PIPELINE
            pass

        return await call_next(request)