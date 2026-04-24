from security.auth import verify_telegram_signature

async def auth_middleware(update: dict, signature: str):

    raw = str(update)

    if not verify_telegram_signature(raw, signature):
        return False

    return True