import hmac
import hashlib
from app.settings import settings

def verify_telegram_signature(data: str, signature: str) -> bool:
    secret = settings.BOT_TOKEN.encode()

    expected = hmac.new(
        secret,
        msg=data.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)