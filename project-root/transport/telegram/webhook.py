@router.post("/webhook")
async def webhook(request: Request):

    try:
        update = await request.json()

        signature = request.headers.get("X-Telegram-Signature", "")

        if not await telegram_security_middleware(update, signature):
            return {"error": "unauthorized"}

        return await handle_update(update)

    except Exception as e:
        return {"error": str(e)}