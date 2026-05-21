import logging

import jwt

from app.settings import settings

logger = logging.getLogger(__name__)


def create_token(user_id: int) -> str:
    return jwt.encode(
        {"sub": str(user_id)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def verify_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception as exc:
        logger.warning("JWT verify failed", extra={"error": str(exc)})
        return None