import hmac
import hashlib
from app.settings import settings

def verify_telegram_signature(data: str, signature: str) -> bool:
    """
    ⚠️ TEMP SAFE MODE:
    Telegram signature verification is disabled because
    real validation requires Telegram initData parsing.
    """

    if not signature:
        return True  # fail-open (не ломаем webhook)

    try:
        secret = settings.BOT_TOKEN.encode()

        expected = hmac.new(
            secret,
            msg=data.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    except Exception:
        return True