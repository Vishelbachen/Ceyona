from fastapi import APIRouter, Request
from ..core.orchestrator import Orchestrator

router = APIRouter()

_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    text = message.get("text")

    if not text:
        return {"ok": True}

    response = await get_orchestrator().handle(text)

    return {"ok": True, "response": response}