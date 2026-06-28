"""
transport/telegram/callback_handler.py

Owns ALL callback_query logic for the bot.

Two responsibilities:
  1. Parsing — parse_callback(): raw Telegram update → typed CallbackContext
  2. Dispatch — dispatch_callback(): CallbackContext → side effects (send/answer)

webhook.py calls parse_callback() + dispatch_callback() and nothing else.
No billing logic, no TON logic, no i18n string selection lives in webhook.py.

architecture.md §26 contract:
  - MAY parse callback_query updates and route to action handlers
  - MUST NOT own orchestration, EPK, or model selection
  - MUST NOT influence routing or TruthMode
"""

import logging
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# ── Types ─────────────────────────────────────────────────────────────────────

SendFn         = Callable[[int, str], Awaitable[None]]
SendWithTopupFn = Callable[[int, str, str], Awaitable[None]]
AnswerFn       = Callable[[str, str], Awaitable[None]]


class CallbackAction(str, Enum):
    BALANCE = "balance"
    HELP    = "help"
    CANCEL  = "cancel"
    TOPUP   = "topup"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CallbackContext:
    action:            CallbackAction
    payload:           str   # anything after the first ":" in callback_data
    callback_query_id: str
    user_id:           int


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_callback(update: dict, user_id: int) -> CallbackContext:
    """
    Parse callback_query update into a typed CallbackContext.
    callback_data format: "action" or "action:payload"
    """
    cq             = update.get("callback_query", {})
    callback_query_id = cq.get("id", "")
    raw_data       = cq.get("data", "")

    parts      = raw_data.split(":", 1)
    action_str = parts[0] if parts else ""
    payload    = parts[1] if len(parts) > 1 else ""

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


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def dispatch_callback(
    ctx:                   CallbackContext,
    chat_id:               int | None,
    user_balance:          float,
    lang:                  str,
    send_message:          SendFn,
    send_message_with_topup: SendWithTopupFn,
    answer_callback:       AnswerFn,
) -> None:
    """
    Execute the side effects for a parsed callback action.

    All TON/billing/i18n logic lives here — never in webhook.py.

    Args:
        ctx:                     Parsed CallbackContext from parse_callback()
        chat_id:                 Telegram chat_id to send follow-up messages to
        user_balance:            Current user balance in USD (fetched upstream in webhook)
        lang:                    Detected UI language code
        send_message:            Async fn(chat_id, text) — webhook._send_message
        send_message_with_topup: Async fn(chat_id, text, lang) — webhook._send_message_with_topup
        answer_callback:         Async fn(callback_query_id, text) — webhook._answer_callback
    """
    from i18n.t import get_system_message

    if ctx.action == CallbackAction.BALANCE:
        # Acknowledge immediately to remove Telegram spinner, then send a
        # proper chat message with the Top Up button so the user can act on it.
        await answer_callback(ctx.callback_query_id, "")
        if chat_id:
            bal_text = f"💰 Balance: ${user_balance:.4f}"
            await send_message_with_topup(chat_id, bal_text, lang)

    elif ctx.action == CallbackAction.TOPUP:
        # Acknowledge immediately — removes Telegram spinner
        await answer_callback(ctx.callback_query_id, "")

        from app.settings import settings as _s
        wallet = _s.ton_wallet
        if wallet:
            # Random suffix prevents memo-guessing attacks:
            # an attacker who knows someone's Telegram ID cannot credit their
            # account by sending TON with just the plain ID as memo.
            _suffix = secrets.token_hex(4)  # e.g. "a3f9c2b1"
            _memo   = f"{ctx.user_id}_{_suffix}"
            topup_text = (
                f"💳 *Top up your balance*\n\n"
                f"1️⃣ Send TON to this address:\n"
                f"`{wallet}`\n\n"
                f"2️⃣ In the comment/memo field, paste this exactly:\n"
                f"`{_memo}`\n\n"
                f"⚠️ *The comment is required.* Without it we cannot credit your account.\n\n"
                f"💰 Current balance: ${user_balance:.4f}"
            )
        else:
            topup_text = get_system_message("topup_unavailable", lang)

        if chat_id:
            await send_message(chat_id, topup_text)

    elif ctx.action == CallbackAction.HELP:
        await answer_callback(
            ctx.callback_query_id,
            get_system_message("help_display", lang),
        )

    elif ctx.action == CallbackAction.CANCEL:
        await answer_callback(
            ctx.callback_query_id,
            get_system_message("cancelled", lang),
        )

    else:
        # UNKNOWN or unhandled — acknowledge silently
        await answer_callback(ctx.callback_query_id, "")