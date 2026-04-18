from fastapi import APIRouter, Request
from ..core.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    text = message.get("text")

    if not text:
        return {"ok": True}

    response = await orchestrator.handle(text)

    return {"ok": True, "response": response}