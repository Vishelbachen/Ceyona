from app.settings import settings


def get(key: str, default: str = "") -> str:
    return getattr(settings, key, default)