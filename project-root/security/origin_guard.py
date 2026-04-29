from app.settings import settings


def _allowed() -> set[str]:
    return {o.strip() for o in settings.allowed_origins.split(",") if o.strip()}


def is_allowed_origin(origin: str) -> bool:
    allowed = _allowed()
    if "*" in allowed:
        return True
    return origin in allowed