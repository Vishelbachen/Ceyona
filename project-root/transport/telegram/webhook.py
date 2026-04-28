import logging

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.settings import settings
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.message_router import UpdateType, classify_update
from transport.telegram.update_handler import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()

_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"

# Webhook secret — set once when registering webhook with Telegram
_WEBHOOK_SECRET = settings.bot_token[:32]   # use first 32 chars as secret


# ─── TELEGRAM API HELPERS ────────────────────────────────────────────────────

async def _send_message(chat_id: int, text: str) -> None:
    """Send a text message to a Telegram chat."""
    if not text:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10.0,
        )


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    """Acknowledge a callback query (removes loading spinner)."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5.0,
        )


def _get_chat_id(update: dict) -> int | None:
    """Extract chat_id from any update type."""
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            return chat["id"]
    cq = update.get("callback_query", {})
    msg = cq.get("message", {})
    return msg.get("chat", {}).get("id")


# ─── WEBHOOK ENDPOINT ────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """
    Main Telegram webhook endpoint.
    Registered at: POST /webhook
    """
    # ── secret token check ───────────────────────────────
    if x_telegram_bot_api_secret_token:
        if not verify_webhook_secret(
            x_telegram_bot_api_secret_token,
            _WEBHOOK_SECRET,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    update: dict = await request.json()
    update_type = classify_update(update)

    if update_type == UpdateType.UNKNOWN:
        return {"ok": True}

    # ── auth ─────────────────────────────────────────────
    auth = verify_update(update)
    if not auth.allowed:
        logger.warning("Rejected update", extra={"reason": auth.reason})
        return {"ok": True}

    chat_id = _get_chat_id(update)
    user_id = auth.user_id

    # ── default user balance (replace with access_controller later) ──
    user_balance: float = 1.0

    # ── route by update type ─────────────────────────────
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        result = await handle_message(
            update=update,
            update_type=update_type,
            user_id=user_id,
            user_balance=user_balance,
        )

        if result.denied:
            reply = (
                "⚠️ Недостаточно средств для выполнения запроса."
                if result.deny_reason == "insufficient_balance"
                else "⚠️ Не удалось обработать запрос."
            )
        else:
            reply = result.text

        if chat_id:
            await _send_message(chat_id, reply)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            await _answer_callback(ctx.callback_query_id, "💰 Баланс: $1.00")
        elif ctx.action == CallbackAction.HELP:
            await _answer_callback(ctx.callback_query_id, "ℹ️ Помощь")
        elif ctx.action == CallbackAction.CANCEL:
            await _answer_callback(ctx.callback_query_id, "✅ Отменено")
        else:
            await _answer_callback(ctx.callback_query_id)

    return {"ok": True}


# ─── WEBHOOK REGISTRATION HELPER ─────────────────────────────────────────────

async def register_webhook() -> bool:
    """
    Register webhook URL with Telegram.
    Call once on startup from bootstrap.py if needed.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_TELEGRAM_API}/setWebhook",
            json={
                "url": f"{settings.webhook_url}/webhook",
                "secret_token": _WEBHOOK_SECRET,
                "allowed_updates": ["message", "edited_message", "callback_query"],
            },
            timeout=10.0,
        )
        data = response.json()
        ok = data.get("ok", False)
        logger.info("Webhook registration", extra={"ok": ok, "response": data})
        return ok