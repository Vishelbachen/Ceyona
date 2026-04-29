import logging

from app.settings import settings

logger = logging.getLogger(__name__)


def _allowed_origins() -> set[str]:
    raw = settings.allowed_origins
    if raw == "*":
        return {"*"}
    return {o.strip() for o in raw.split(",") if o.strip()}


def is_origin_allowed(origin: str) -> bool:
    allowed = _allowed_origins()
    if "*" in allowed:
        return True
    return origin in allowed