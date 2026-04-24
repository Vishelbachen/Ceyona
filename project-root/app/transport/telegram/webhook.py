from fastapi import APIRouter, Request
from transport.telegram.router import handle_update

router = APIRouter()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    return await handle_update(update)