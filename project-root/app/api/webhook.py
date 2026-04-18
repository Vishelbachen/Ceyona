from fastapi import APIRouter, Request
from app.core.orchestrator import Orchestrator

router = APIRouter()

orchestrator = Orchestrator()


@router.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    message = data.get("message", {}).get("text")

    if not message:
        return {"error": "empty_message"}

    response = await orchestrator.handle(
        user_input=message,
        mode="fast"
    )

    return {"response": response}