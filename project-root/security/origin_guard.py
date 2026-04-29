from app.settings import settings


def _allowed_origins() -> set[str]:
    return {o.strip() for o in settings.allowed_origins.split(",") if o.strip()}


def is_allowed_origin(origin: str) -> bool:
    """Check if origin is in allowed list. '*' allows all."""
    origins = _allowed_origins()
    return "*" in origins or origin in origins