import logging
import re

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from lingua import Language, LanguageDetectorBuilder

from app.settings import settings
from observability.metrics import gauge, increment
from observability.tracing import trace
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.message_router import UpdateType, classify_update, extract_text
from transport.telegram.update_handler import handle_message

# Build detector once at import time (expensive operation)
_detector = (
    LanguageDetectorBuilder
    .from_all_languages()
    .with_minimum_relative_distance(0.15)
    .build()
)

logger = logging.getLogger(__name__)

router = APIRouter()

_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"

_WEBHOOK_SECRET = re.sub(r"[^A-Za-z0-9_\-]", "_", settings.bot_token)[:256]


async def _send_message(chat_id: int, text: str) -> None:
    if not text:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10.0,
        )


async def _send_message_with_topup(chat_id: int, text: str, lang: str = "en") -> None:
    """Send message with an inline 'Top Up' button linking to TON wallet."""
    if not text:
        return
    from i18n.t import t as _t

    topup_label = _t("topup_button", lang)

    keyboard = {
        "inline_keyboard": [[
            {
                "text": topup_label,
                "callback_data": "topup",
            }
        ]]
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            },
            timeout=10.0,
        )



async def _send_voice(chat_id: int, audio_bytes: bytes, caption: str = "") -> bool:
    """
    Send a voice message via Telegram sendVoice.
    Returns True on success, False on failure.
    Falls back gracefully — caller sends text if this returns False.
    """
    try:
        import io
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_TELEGRAM_API}/sendVoice",
                data={"chat_id": chat_id, "caption": caption},
                files={"voice": ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg")},
                timeout=30.0,
            )
            return response.status_code == 200
    except Exception as exc:
        logger.warning("_send_voice failed", extra={"error": str(exc)})
        return False


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


# ─── LINGUA ISO MAP ───────────────────────────────────────────────────────────
# All 75 Language attributes verified against lingua-language-detector 2.x enum.
# Languages without a bot-supported ISO code map to closest supported lang or
# are omitted (detector returns them but _LINGUA_ISO.get() falls back to profile_lang).
_LINGUA_ISO: dict[Language, str] = {
    Language.AFRIKAANS:  "af",
    Language.ALBANIAN:   "sq",
    Language.ARABIC:     "ar",
    Language.ARMENIAN:   "hy",
    Language.AZERBAIJANI:"az",
    Language.BASQUE:     "eu",
    Language.BELARUSIAN: "be",
    Language.BENGALI:    "bn",
    Language.BOKMAL:     "no",
    Language.BOSNIAN:    "bs",
    Language.BULGARIAN:  "bg",
    Language.CATALAN:    "ca",
    Language.CHINESE:    "zh",
    Language.CROATIAN:   "hr",
    Language.CZECH:      "cs",
    Language.DANISH:     "da",
    Language.DUTCH:      "nl",
    Language.ENGLISH:    "en",
    Language.ESPERANTO:  "eo",
    Language.ESTONIAN:   "et",
    Language.FINNISH:    "fi",
    Language.FRENCH:     "fr",
    Language.GANDA:      "lg",   # Luganda — no bot support, falls back to profile
    Language.GEORGIAN:   "ka",
    Language.GERMAN:     "de",
    Language.GREEK:      "el",
    Language.GUJARATI:   "gu",
    Language.HEBREW:     "he",
    Language.HINDI:      "hi",
    Language.HUNGARIAN:  "hu",
    Language.ICELANDIC:  "is",
    Language.INDONESIAN: "id",
    Language.IRISH:      "ga",
    Language.ITALIAN:    "it",
    Language.JAPANESE:   "ja",
    Language.KAZAKH:     "kk",
    Language.KOREAN:     "ko",
    Language.LATIN:      "la",
    Language.LATVIAN:    "lv",
    Language.LITHUANIAN: "lt",
    Language.MACEDONIAN: "mk",
    Language.MALAY:      "ms",
    Language.MAORI:      "mi",
    Language.MARATHI:    "mr",
    Language.MONGOLIAN:  "mn",
    Language.NYNORSK:    "no",
    Language.PERSIAN:    "fa",
    Language.POLISH:     "pl",
    Language.PORTUGUESE: "pt",
    Language.PUNJABI:    "pa",
    Language.ROMANIAN:   "ro",
    Language.RUSSIAN:    "ru",
    Language.SERBIAN:    "sr",
    Language.SHONA:      "sn",
    Language.SLOVAK:     "sk",
    Language.SLOVENE:    "sl",
    Language.SOMALI:     "so",
    Language.SOTHO:      "st",
    Language.SPANISH:    "es",
    Language.SWAHILI:    "sw",
    Language.SWEDISH:    "sv",
    Language.TAGALOG:    "tl",
    Language.TAMIL:      "ta",
    Language.TELUGU:     "te",
    Language.THAI:       "th",
    Language.TSONGA:     "ts",
    Language.TSWANA:     "tn",
    Language.TURKISH:    "tr",
    Language.UKRAINIAN:  "uk",
    Language.URDU:       "ur",
    Language.VIETNAMESE: "vi",
    Language.WELSH:      "cy",
    Language.XHOSA:      "xh",
    Language.YORUBA:     "yo",
    Language.ZULU:       "zu",
}


def _detect_lang(update: dict) -> str:
    """
    Detect language of incoming message.

    Priority:
      1. lingua detection on message text (75 languages)
      2. Telegram profile language_code (UI language, fallback)
      3. "en" as final fallback
    """
    text = ""
    profile_lang = "en"

    for key in ("message", "edited_message", "callback_query"):
        entry = update.get(key, {})
        user = entry.get("from") or {}
        code = user.get("language_code", "")
        if code:
            profile_lang = code.split("-")[0].lower()
        if not text:
            text = (entry.get("text") or entry.get("caption") or "").strip()

    if not text or len(text) < 3:
        return profile_lang

    try:
        detected = _detector.detect_language_of(text)
        if detected is not None:
            iso = _LINGUA_ISO.get(detected)
            if iso:
                return iso
            # lingua recognised a language but we have no ISO mapping for it
            # (e.g. GANDA/Luganda) — fall through to profile_lang below
        else:
            # lingua returned None: language is unrecognised (e.g. Inuktitut,
            # Greenlandic, invented text).  For very short inputs there is a
            # high risk of a wrong embedding-based intent match (e.g. MAPS),
            # so we flag this by returning profile_lang.  The downstream
            # intent classifier receives lang_uncertain=False (profile_lang
            # is still a valid lang code), but classify() will apply a higher
            # confidence threshold for short unrecognised texts — see
            # cognition/intent_engine.py classify().
            logger.info(
                "lingua: language unrecognised, falling back to profile_lang",
                extra={"text_preview": text[:30], "profile_lang": profile_lang},
            )
    except Exception as exc:
        logger.warning("lingua detection failed", extra={"error": str(exc)})

    return profile_lang


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if x_telegram_bot_api_secret_token:
        if not verify_webhook_secret(x_telegram_bot_api_secret_token, _WEBHOOK_SECRET):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        update: dict = await request.json()
    except Exception as exc:
        logger.error("Failed to parse update JSON", extra={"error": str(exc)})
        return {"ok": True}

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
    hf_client = request.app.state.hf_client

    # Fix §10.4: generate request_id for full pipeline log correlation.
    # Format: "{update_id}:{user_id}" — unique per Telegram update.
    _update_id = str(update.get("update_id", ""))
    request_id = f"{_update_id}:{user_id}" if _update_id else str(user_id)
    logger.info("Incoming message", extra={"request_id": request_id, "user_id": user_id, "lang": lang})

    # ── rate limiting ─────────────────────────────────────────────────────────
    from cognition.response_synthesizer import get_system_message
    from security.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter and not await limiter.is_allowed(user_id):
        if chat_id:
            await _send_message(chat_id, get_system_message("rate_limited", lang))
        return {"ok": True}

    # ── balance ───────────────────────────────────────────────────────────────
    user_balance = 0.0
    try:
        from payments.access_controller import AccessController
        ac = AccessController(supabase)
        balance_result = await ac.get_balance(user_id)
        user_balance = balance_result.balance_usd
    except Exception as exc:
        logger.error("Balance fetch failed", extra={"error": str(exc)})

    # ── bot commands — handled BEFORE Safety Gate ────────────────────────────
    # /balance, /start, /help etc. are system commands, not user content.
    # They must never be routed through the Safety Gate.
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE) and chat_id:
        raw_text = extract_text(update).strip()
        if raw_text.startswith("/balance"):
            bal_text = f"💰 Balance: ${user_balance:.4f}"
            await _send_message(chat_id, bal_text)
            return {"ok": True}
        if raw_text.startswith("/start"):
            await _send_message(chat_id, get_system_message("help_display", lang))
            return {"ok": True}
        if raw_text.startswith("/help"):
            await _send_message(chat_id, get_system_message("help_display", lang))
            return {"ok": True}

    # ── message handling ──────────────────────────────────────────────────────
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        import time as _time
        _req_start = _time.perf_counter()
        increment("webhook.requests")
        try:
            with trace("handle_message", request_id=request_id, user_id=str(user_id), lang=lang):
                result = await handle_message(
                    update=update,
                    update_type=update_type,
                    user_id=user_id,
                    user_balance=user_balance,
                    lang=lang,
                    supabase=supabase,
                    redis=request.app.state.redis,
                    hf_client=hf_client,
                    request_id=request_id,
                )
        except Exception as exc:
            logger.error("handle_message crashed", extra={"error": str(exc)})
            increment("webhook.errors")
            if chat_id:
                await _send_message(
                    chat_id,
                    get_system_message("no_response", lang),
                )
            return {"ok": True}
        finally:
            gauge("webhook.last_latency_ms", round((_time.perf_counter() - _req_start) * 1000, 2))

        # ── billing ───────────────────────────────────────────────────────────
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
                    intent=result.intent,
                    audio_seconds=result.audio_seconds,
                    tts_characters=result.tts_characters,
                    tool_calls=result.tool_calls,
                ))
            except Exception as exc:
                logger.error("Billing failed", extra={"error": str(exc)})

        # Track denied/allowed outcomes
        if result.denied:
            increment(f"webhook.denied.{result.deny_reason or 'unknown'}")
        else:
            increment("webhook.allowed")
        logger.info("Request complete", extra={
            "request_id": request_id,
            "denied":     result.denied,
            "tier":       result.tier.value if result.tier else "",
            "model":      result.model,
            "intent":     result.intent,
            "cost_usd":   f"{result.usage.cost_usd:.6f}",
        })

        if chat_id:
            # Low balance warning — show topup button when balance drops below $0.10
            try:
                from payments.access_controller import AccessController
                ac2 = AccessController(supabase)
                fresh_balance = await ac2.get_balance(user_id)
                if 0 < fresh_balance.balance_usd < 0.10:
                    from i18n.t import t as _t
                    low_balance_text = _t("low_balance_warning", lang)
                    await _send_message_with_topup(chat_id, low_balance_text, lang)
            except Exception:
                pass  # non-critical, never block response

            # TTS audio: send voice message if audio was synthesized, text as fallback
            tts_bytes = getattr(result, "tts_audio_bytes", b"")
            if tts_bytes:
                sent_audio = await _send_voice(chat_id, tts_bytes)
                if not sent_audio:
                    # sendVoice failed — fall back to text silently
                    logger.warning("sendVoice failed — falling back to text", extra={"chat_id": chat_id})
                    await _send_message(chat_id, result.text)
            else:
                await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            bal_text = f"💰 Balance: ${user_balance:.2f}"
            await _answer_callback(ctx.callback_query_id, bal_text)
        elif ctx.action == CallbackAction.HELP:
            await _answer_callback(
                ctx.callback_query_id,
                get_system_message("help_display", lang),
            )
        elif ctx.action == CallbackAction.CANCEL:
            await _answer_callback(
                ctx.callback_query_id,
                get_system_message("cancelled", lang),
            )
        else:
            await _answer_callback(ctx.callback_query_id)

    return {"ok": True}


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