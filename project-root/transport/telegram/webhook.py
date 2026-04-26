from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException

from transport.telegram.update_handler import UpdateHandler
from security.origin_guard import OriginGuard


# =========================
# ROUTER
# =========================
router = APIRouter()


# =========================
# DEPENDENCIES (INJECTED VIA BOOTSTRAP)
# =========================
update_handler = UpdateHandler()
origin_guard = OriginGuard()


# =========================
# TELEGRAM WEBHOOK ENTRYPOINT
# =========================
@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    ROLE:
    - receive raw Telegram updates
    - validate origin (light security gate)
    - forward payload to update handler

    STRICT RULES:
    - no business logic
    - no payments logic
    - no LLM calls
    - no decision making
    """

    origin = request.headers.get("origin")

    origin_check = origin_guard.validate(origin)

    if not origin_check.is_allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden origin: {origin_check.reason}",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # forward to domain-ingestion layer
    await update_handler.handle(payload)

    return {"status": "ok"}