import logging
from enum import Enum

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    MESSAGE = "message"
    CALLBACK_QUERY = "callback_query"
    EDITED_MESSAGE = "edited_message"
    UNKNOWN = "unknown"


def classify_update(update: dict) -> UpdateType:
    """Classify incoming Telegram update by type."""
    if "message" in update:
        return UpdateType.MESSAGE
    if "callback_query" in update:
        return UpdateType.CALLBACK_QUERY
    if "edited_message" in update:
        return UpdateType.EDITED_MESSAGE
    return UpdateType.UNKNOWN


def extract_text(update: dict) -> str:
    """Extract plain text from message or edited_message."""
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        text = msg.get("text") or msg.get("caption") or ""
        if text:
            return text
    return ""


def extract_photo(update: dict) -> dict | None:
    """
    Extract photo metadata from a message update.
    Returns the largest available photo file_id dict, or None.
    Telegram sends photos as array of sizes — we pick the last (largest).
    """
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        photos = msg.get("photo")
        if photos:
            # Telegram provides multiple resolutions; last = highest quality
            best = photos[-1]
            return {
                "file_id": best.get("file_id", ""),
                "file_unique_id": best.get("file_unique_id", ""),
                "width": best.get("width", 0),
                "height": best.get("height", 0),
                "caption": msg.get("caption", ""),
            }
    return None


def has_photo(update: dict) -> bool:
    """Return True if this update contains a photo."""
    return extract_photo(update) is not None


def extract_callback_data(update: dict) -> str:
    """Extract callback_data from callback_query update."""
    return update.get("callback_query", {}).get("data", "")