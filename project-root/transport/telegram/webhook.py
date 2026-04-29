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
_WEBHOOK_SECRET = settings.bot_token[:32]


# ─── TELEGRAM API HELPERS ────────────────────────────────────────────────────

async def _send_message(chat_id: int, text: str) -> None:
    if not text:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10.0,
        )


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5.0,
        )


def _get_chat_id(update: dict) -> int | None:
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            return chat["id"]
    cq = update.get("callback_query", {})
    msg = cq.get("message", {})
    return msg.get("chat", {}).get("id")


def _detect_lang(update: dict) -> str:
    """Extract language_code from any update type."""
    for key in ("message", "edited_message", "callback_query"):
        entry = update.get(key, {})
        user = entry.get("from") or {}
        code = user.get("language_code", "")
        if code:
            return code.split("-")[0].lower()
    return "en"


# ─── WEBHOOK ENDPOINT ────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
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

    auth = verify_update(update)
    if not auth.allowed:
        logger.warning("Rejected update", extra={"reason": auth.reason})
        return {"ok": True}

    chat_id = _get_chat_id(update)
    user_id = auth.user_id
    lang = _detect_lang(update)

    user_balance: float = 1.0

    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        result = await handle_message(
            update=update,
            update_type=update_type,
            user_id=user_id,
            user_balance=user_balance,
            lang=lang,
        )

        if chat_id:
            await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        from cognition.response_synthesizer import get_system_message
        if ctx.action == CallbackAction.BALANCE:
            await _answer_callback(ctx.callback_query_id, get_system_message("balance_display", lang))
        elif ctx.action == CallbackAction.HELP:
            await _answer_callback(ctx.callback_query_id, get_system_message("help_display", lang))
        elif ctx.action == CallbackAction.CANCEL:
            await _answer_callback(ctx.callback_query_id, get_system_message("cancelled", lang))
        else:
            await _answer_callback(ctx.callback_query_id)

    return {"ok": True}


# ─── WEBHOOK REGISTRATION ─────────────────────────────────────────────────────

async def register_webhook() -> bool:
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