import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.settings import settings
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.client import answer_callback, send_message, send_typing
from transport.telegram.command_handler import (
    extract_command,
    get_clear_message,
    get_help_message,
    get_start_message,
    get_unknown_cmd_message,
    is_command,
)
from transport.telegram.message_router import UpdateType, classify_update
from transport.telegram.update_handler import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()

_WEBHOOK_SECRET = settings.bot_token[:32]


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


def _extract_text(update: dict) -> str:
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        text = msg.get("text") or msg.get("caption") or ""
        if text:
            return text
    return ""


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if x_telegram_bot_api_secret_token:
        if not verify_webhook_secret(x_telegram_bot_api_secret_token, _WEBHOOK_SECRET):
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
    supabase = request.app.state.supabase

    # ── rate limiting ─────────────────────────────────────
    from cognition.response_synthesizer import get_system_message
    from security.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter and not await limiter.is_allowed(user_id):
        if chat_id:
            await send_message(chat_id, get_system_message("rate_limited", lang))
        return {"ok": True}

    # ── real balance ──────────────────────────────────────
    user_balance = 0.0
    try:
        from payments.access_controller import AccessController
        ac = AccessController(supabase)
        balance_result = await ac.get_balance(user_id)
        user_balance = balance_result.balance_usd
    except Exception as exc:
        logger.error("Balance fetch failed", extra={"error": str(exc)})

    # ── command handling ──────────────────────────────────
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        raw_text = _extract_text(update)

        if raw_text and is_command(raw_text):
            cmd, _ = extract_command(raw_text)

            if cmd == "/start":
                if chat_id:
                    await send_message(chat_id, get_start_message(lang))

            elif cmd == "/help":
                if chat_id:
                    await send_message(chat_id, get_help_message(lang))

            elif cmd == "/balance":
                if chat_id:
                    await send_message(
                        chat_id,
                        f"💰 Balance: ${user_balance:.2f}",
                    )

            elif cmd == "/clear":
                if chat_id:
                    try:
                        from memory.conversation_history import ConversationHistory
                        ch = ConversationHistory(supabase)
                        await ch.clear(user_id)
                    except Exception as exc:
                        logger.error("History clear failed", extra={"error": str(exc)})
                    await send_message(chat_id, get_clear_message(lang))

            else:
                if chat_id:
                    await send_message(chat_id, get_unknown_cmd_message(lang))

            return {"ok": True}

        # ── typing indicator before LLM ───────────────────
        if chat_id:
            await send_typing(chat_id)

        # ── normal message handling ───────────────────────
        result = await handle_message(
            update=update,
            update_type=update_type,
            user_id=user_id,
            user_balance=user_balance,
            lang=lang,
            supabase=supabase,
        )

        # ── billing ───────────────────────────────────────
        if not result.denied and result.usage.cost_usd > 0:
            try:
                from payments.access_controller import AccessController
                from payments.usage_meter import UsageEntry, UsageMeter

                ac = AccessController(supabase)
                await ac.deduct(user_id, result.usage.cost_usd)

                meter = UsageMeter(supabase)
                billed = meter.compute_billed(result.usage.cost_usd)
                await meter.record(UsageEntry(
                    user_id=user_id,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    embedding_tokens=result.usage.embedding_tokens,
                    rerank_tokens=result.usage.rerank_tokens,
                    tier=result.usage.tier,
                    embedding_type=result.usage.embedding_type,
                    raw_cost_usd=result.usage.cost_usd,
                    billed_cost_usd=billed,
                    model=result.model,
                    lang=result.lang,
                ))
            except Exception as exc:
                logger.error("Billing failed", extra={"error": str(exc)})

        if chat_id:
            await send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            await answer_callback(
                ctx.callback_query_id,
                f"💰 ${user_balance:.2f}",
            )
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
            await answer_callback(ctx.callback_query_id)

    return {"ok": True}


async def register_webhook() -> bool:
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.bot_token}/setWebhook",
            json={
                "url": f"{settings.webhook_url}/webhook",
                "secret_token": _WEBHOOK_SECRET,
                "allowed_updates": ["message", "edited_message", "callback_query"],
            },
            timeout=10.0,
        )
        data = response.json()
        ok = data.get("ok", False)
        logger.info("Webhook registration", extra={"ok": ok})
        return ok