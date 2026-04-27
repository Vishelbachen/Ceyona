from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.bootstrap import get_container
from app.settings import get_settings


# =========================
# INIT
# =========================
settings = get_settings()
container = get_container()

app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)


# =========================
# HEALTH
# =========================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-platform",
    }


# =========================
# CHAT ENDPOINT
# =========================
@app.post("/chat")
async def chat(payload: dict):
    user_id = payload.get("user_id", "anonymous")
    message = payload.get("message", "")
    origin = payload.get("origin")

    # ORIGIN CHECK
    origin_result = container.origin_guard.validate(origin)
    if not origin_result.is_allowed:
        return {
            "error": "origin_not_allowed",
            "reason": origin_result.reason,
        }

    # RATE LIMIT
    if not container.rate_limiter.allow(user_id):
        return {
            "error": "rate_limited",
        }

    # ACCESS CHECK
    access = container.access_controller.check(user_id)

    if not access.allowed:
        return {
            "error": "access_denied",
            "reason": access.reason,
        }

    # MAIN EXECUTION
    try:
        result = await container.orchestrator.run(
            user_id=user_id,
            message=message,
        )

    except Exception as e:
        return {
            "error": "orchestrator_failed",
            "detail": str(e),
        }

    # COMMIT ONLY ON SUCCESS
    container.access_controller.commit(user_id)

    # usage tracking (temporary safe placeholder)
    container.usage_meter.record(
        user_id=user_id,
        cost=getattr(result, "cost", 0.0) if hasattr(result, "cost") else 0.0,
    )

    return {
        "response": result,
        "limits": {
            "daily_remaining": access.remaining_daily,
            "monthly_remaining": access.remaining_monthly,
        },
    }


# =========================
# RUN
# =========================
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )