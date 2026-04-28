from fastapi import APIRouter, Request, HTTPException
from starlette.responses import JSONResponse

from app.bootstrap import get_container

# =========================
# ROUTER
# =========================
router = APIRouter()

container = get_container()


# =========================
# TELEGRAM WEBHOOK ENTRYPOINT
# =========================
@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Transport layer only:
    - receives Telegram update
    - validates payload existence
    - forwards to message router
    """

    try:
        update = await request.json()

        if not update:
            raise HTTPException(status_code=400, detail="Empty payload")

        # =========================
        # DELEGATION ONLY
        # No logic, no parsing decisions
        # =========================
        message_router = container.orchestrator

        # forward raw update to orchestrator pipeline
        result = await message_router.handle_update(update)

        return JSONResponse(
            content={
                "status": "ok",
                "processed": True,
                "result": result,
            }
        )

    except Exception as e:
        # transport layer safe fallback
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
            },
        )