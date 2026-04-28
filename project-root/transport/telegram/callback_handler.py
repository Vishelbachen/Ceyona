import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CallbackAction(str, Enum):
    BALANCE = "balance"
    HELP = "help"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CallbackContext:
    action: CallbackAction
    payload: str          # anything after the first ":" in callback_data
    callback_query_id: str
    user_id: int


def parse_callback(update: dict, user_id: int) -> CallbackContext:
    """
    Parse callback_query update into a typed CallbackContext.
    callback_data format: "action" or "action:payload"
    """
    cq = update.get("callback_query", {})
    callback_query_id = cq.get("id", "")
    raw_data = cq.get("data", "")

    parts = raw_data.split(":", 1)
    action_str = parts[0] if parts else ""
    payload = parts[1] if len(parts) > 1 else ""

    try:
        action = CallbackAction(action_str)
    except ValueError:
        logger.warning("Unknown callback action", extra={"raw_data": raw_data})
        action = CallbackAction.UNKNOWN

    return CallbackContext(
        action=action,
        payload=payload,
        callback_query_id=callback_query_id,
        user_id=user_id,
    )