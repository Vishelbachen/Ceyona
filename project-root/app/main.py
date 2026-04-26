from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.bootstrap import get_container
from infra.config_loader import get_settings


# =========================
# APP INIT (ZERO BUSINESS LOGIC)
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
# HEALTH CHECK
# =========================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-platform",
    }


# =========================
# CORE ENTRYPOINT (EXAMPLE PIPELINE HOOK)
# =========================
@app.post("/chat")
async def chat(payload: dict):
    """
    Minimal transport layer endpoint.

    ROLE:
    - receive request
    - delegate to orchestrator
    - return response

    DOES NOT:
    - interpret logic
    - decide routing
    - touch internal layers directly
    """

    user_id = payload.get("user_id", "anonymous")
    message = payload.get("message", "")
    origin = payload.get("origin")

    # =========================
    # ORIGIN CHECK
    # =========================
    origin_result = container.origin_guard.validate(origin)
    if not origin_result.is_allowed:
        return {
            "error": "origin_not_allowed",
            "reason": origin_result.reason,
        }

    # =========================
    # RATE LIMIT CHECK
    # =========================
    if not container.rate_limiter.allow(user_id):
        return {
            "error": "rate_limited",
        }

    # =========================
    # ACCESS CHECK (BILLING LAYER)
    # =========================
    access = container.access_controller.check(user_id)

    if not access.allowed:
        return {
            "error": "access_denied",
            "reason": access.reason,
        }

    # =========================
    # MAIN ORCHESTRATION CALL
    # =========================
    result = await container.orchestrator.run(
        user_id=user_id,
        message=message,
    )

    # =========================
    # COMMIT USAGE (AFTER SUCCESS)
    # =========================
    container.access_controller.commit(user_id)

    # optional telemetry
    container.usage_meter.record(
        user_id=user_id,
        cost=0.0,  # placeholder until pricing hook is wired per request
    )

    return {
        "response": result,
        "limits": {
            "daily_remaining": access.remaining_daily,
            "monthly_remaining": access.remaining_monthly,
        },
    }


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )