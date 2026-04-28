from fastapi import APIRouter, Request, HTTPException
from starlette.responses import JSONResponse

from app.bootstrap import get_container

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Transport layer only.
    """

    try:
        update = await request.json()

        if not update:
            raise HTTPException(status_code=400, detail="Empty payload")

        container = get_container()
        orchestrator = container.orchestrator

        result = await orchestrator.handle_update(update)

        return JSONResponse(
            content={
                "status": "ok",
                "processed": True,
                "result": result,
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
            },
        )