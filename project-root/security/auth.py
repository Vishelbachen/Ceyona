import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from app.settings import settings

logger = logging.getLogger(__name__)
_ALGORITHM = "HS256"
_EXPIRY_HOURS = 24


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    username: str | None


def create_token(user_id: int, username: str | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        return TokenPayload(
            user_id=int(payload["sub"]),
            username=payload.get("username"),
        )
    except Exception as exc:
        logger.warning("Token verification failed", extra={"error": str(exc)})
        return None