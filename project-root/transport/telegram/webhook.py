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

    # ── real balance from Supabase ───────────────────────
    user_balance: float = 1.0  # safe default
    try:
        access_controller = request.app.state.access_controller
        balance_result = await access_controller.get_balance(user_id)
        user_balance = balance_result.balance_usd
    except Exception as exc:
        logger.warning("Balance fetch failed, using default", extra={"error": str(exc)})

    # ── conversation history ─────────────────────────────
    conversation_history: list[dict] = []
    try:
        conv_history = request.app.state.conversation_history
        conversation_history = await conv_history.get(user_id)
    except Exception as exc:
        logger.warning("History fetch failed", extra={"error": str(exc)})

    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        result = await handle_message(
            update=update,
            update_type=update_type,
            user_id=user_id,
            user_balance=user_balance,
            lang=lang,
            conversation_history=conversation_history,
        )

        # ── save turns to history ────────────────────────
        if not result.denied:
            try:
                conv_history = request.app.state.conversation_history
                from transport.telegram.message_router import extract_text
                user_text = extract_text(update)
                await conv_history.append(user_id, "user", user_text)
                if result.text:
                    await conv_history.append(user_id, "assistant", result.text)
            except Exception as exc:
                logger.warning("History save failed", extra={"error": str(exc)})

        # ── deduct balance after successful execution ────
        if not result.denied and result.usage.cost_usd > 0:
            try:
                access_controller = request.app.state.access_controller
                await access_controller.deduct(user_id, result.usage.cost_usd)
            except Exception as exc:
                logger.warning("Balance deduct failed", extra={"error": str(exc)})

        # ── record usage ─────────────────────────────────
        if not result.denied:
            try:
                from payments.usage_meter import UsageEntry
                usage_meter = request.app.state.usage_meter
                billed = usage_meter.compute_billed(result.usage.cost_usd)
                await usage_meter.record(UsageEntry(
                    user_id=user_id,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    embedding_tokens=result.usage.embedding_tokens,
                    rerank_tokens=result.usage.rerank_tokens,
                    tier=result.tier,
                    embedding_type=result.usage.embedding_type,
                    raw_cost_usd=result.usage.cost_usd,
                    billed_cost_usd=billed,
                    model=result.model,
                    lang=result.lang,
                ))
            except Exception as exc:
                logger.warning("Usage record failed", extra={"error": str(exc)})

        if chat_id:
            await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        from cognition.response_synthesizer import get_system_message
        if ctx.action == CallbackAction.BALANCE:
            try:
                access_controller = request.app.state.access_controller
                balance_result = await access_controller.get_balance(user_id)
                bal = balance_result.balance_usd
                bal_text = f"💰 Balance: ${bal:.2f}"
            except Exception:
                bal_text = get_system_message("balance_display", lang)
            await _answer_callback(ctx.callback_query_id, bal_text)
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