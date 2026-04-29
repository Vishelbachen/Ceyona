import hashlib
import hmac
import logging
import time

from app.settings import settings

logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data: str) -> bool:
    """
    Verify Telegram WebApp init data signature.
    Used for web-based auth flows.
    """
    try:
        from urllib.parse import parse_qsl
        params = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = params.pop("hash", "")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

        secret = hmac.new(
            b"WebAppData",
            settings.bot_token.encode(),
            hashlib.sha256,
        ).digest()

        expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received_hash)
    except Exception as exc:
        logger.warning("init_data verification failed", extra={"error": str(exc)})
        return False


def sign_token(user_id: int) -> str:
    """Simple HMAC token for internal service calls."""
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(
        settings.jwt_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{sig}"


def verify_token(token: str, max_age: int = 3600) -> int | None:
    """Verify internal token. Returns user_id or None."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id_str, ts_str, sig = parts
        payload = f"{user_id_str}:{ts_str}"

        expected_sig = hmac.new(
            settings.jwt_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, sig):
            return None

        if int(time.time()) - int(ts_str) > max_age:
            return None

        return int(user_id_str)
    except Exception:
        return None