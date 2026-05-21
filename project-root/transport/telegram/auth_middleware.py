import hmac
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthResult:
    allowed: bool
    user_id: int | None = None
    username: str | None = None
    reason: str = ""


def _extract_user(update: dict) -> tuple[int | None, str | None]:
    """Pull user_id and username from any update type."""
    for key in ("message", "callback_query", "edited_message"):
        entry = update.get(key)
        if entry:
            user = entry.get("from") or {}
            return user.get("id"), user.get("username")
    return None, None


def verify_update(update: dict) -> AuthResult:
    """
    Validate incoming Telegram update.
    Currently: extract user_id and confirm it exists.
    Extend here for whitelist / ban checks using Redis or Supabase.
    """
    user_id, username = _extract_user(update)

    if user_id is None:
        logger.warning("Update with no user_id rejected")
        return AuthResult(allowed=False, reason="no_user_id")

    return AuthResult(
        allowed=True,
        user_id=user_id,
        username=username,
    )


def verify_webhook_secret(token: str, expected: str) -> bool:
    """
    Compare webhook secret token using constant-time comparison.
    Pass X-Telegram-Bot-Api-Secret-Token header value here.
    """
    return hmac.compare_digest(token.encode(), expected.encode())