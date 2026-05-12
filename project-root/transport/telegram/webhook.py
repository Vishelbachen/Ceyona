import logging
import re

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

# secret_token: only A-Z a-z 0-9 _ - allowed, max 256 chars
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


# Script → language code mapping for script-based language detection.
# Used when the message text contains non-Latin characters that unambiguously
# identify the language, overriding the Telegram profile language_code.
_SCRIPT_LANG_MAP: tuple[tuple[range, str], ...] = (
    (range(0x0400, 0x0500), "ru"),   # Cyrillic → ru (refined below)
    (range(0x0500, 0x0530), "ru"),   # Cyrillic supplement
    (range(0x10A0, 0x10FF), "ka"),   # Georgian
    (range(0x0530, 0x058F), "hy"),   # Armenian
    (range(0x0600, 0x06FF), "ar"),   # Arabic
    (range(0x0590, 0x05FF), "he"),   # Hebrew
    (range(0x0900, 0x097F), "hi"),   # Devanagari
    (range(0x0980, 0x09FF), "bn"),   # Bengali
    (range(0x0600, 0x06FF), "fa"),   # Persian (overlaps Arabic — handled by profile)
    (range(0x4E00, 0x9FFF), "zh"),   # CJK Unified (Chinese)
    (range(0x3040, 0x30FF), "ja"),   # Hiragana/Katakana
    (range(0xAC00, 0xD7AF), "ko"),   # Hangul
    (range(0x0E00, 0x0E7F), "th"),   # Thai
    (range(0x1200, 0x137F), "am"),   # Ethiopic
    (range(0x1800, 0x18AF), "mn"),   # Mongolian script
)

# Cyrillic-script languages — disambiguated by profile language_code
_CYRILLIC_LANGS: frozenset[str] = frozenset(
    {"ru", "uk", "bg", "sr", "mk", "kk", "ky", "mn", "tg", "uz", "ba"}
)


# Languages written in Latin script that Telegram may misreport.
# Matched by characteristic vocabulary — checked ONLY when script detection
# returns None (i.e. the message is predominantly Latin-script).
# Tuples of (lang_code, frozenset_of_signals).
_LATIN_LANG_SIGNALS: tuple[tuple[str, frozenset[str]], ...] = (
    ("ha", frozenset({
        "yanayi", "yanzu", "wane", "ina", "gari", "ruwan", "zafi",
        "sanyi", "saukar", "sama", "iska", "tsananin",
    })),
    ("yo", frozenset({
        "ojo", "ojo ojo", "ise", "ilu", "omi", "afefe", "orun",
        "igba", "bawo", "nibo", "kini",
    })),
    ("ig", frozenset({
        "gini", "obi", "mmiri", "ikuku", "oge", "ebe", "oji",
        "otutu", "okpomoku",
    })),
    ("sw", frozenset({
        "hali ya hewa", "joto", "baridi", "upepo", "mvua",
        "nchi", "mji", "sasa", "leo",
    })),
    ("id", frozenset({
        "cuaca", "sekarang", "suhu", "angin", "hujan", "kota",
        "hari", "malam", "pagi",
    })),
    ("ms", frozenset({
        "cuaca", "sekarang", "suhu", "angin", "hujan", "bandar",
        "hari ini", "petang", "pagi",
    })),
    ("vi", frozenset({
        "thời tiết", "nhiệt độ", "gió", "mưa", "thành phố",
        "bây giờ", "hôm nay",
    })),
    ("th", frozenset({
        "อากาศ", "อุณหภูมิ", "ลม", "ฝน", "ตอนนี้", "วันนี้",
    })),
    ("fi", frozenset({
        "sää", "lämpötila", "tuuli", "sade", "kaupunki", "nyt", "tänään",
    })),
    ("hu", frozenset({
        "időjárás", "hőmérséklet", "szél", "eső", "város", "most", "ma",
    })),
    ("cs", frozenset({
        "počasí", "teplota", "vítr", "déšť", "město", "nyní", "dnes",
    })),
    ("ro", frozenset({
        "vreme", "temperatură", "vânt", "ploaie", "oraș", "acum", "azi",
    })),
    ("sk", frozenset({
        "počasie", "teplota", "vietor", "dážď", "mesto", "teraz", "dnes",
    })),
)


def _detect_lang_from_script(text: str, profile_lang: str) -> str | None:
    """
    Detect language from message script.
    Returns a lang code if the script is unambiguous, None otherwise.
    """
    if not text or len(text) < 3:
        return None
    # Count characters in each script range
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for char_range, lang in _SCRIPT_LANG_MAP:
            if cp in char_range:
                counts[lang] = counts.get(lang, 0) + 1
                break
    if not counts:
        return None
    dominant = max(counts, key=lambda k: counts[k])
    dominant_count = counts[dominant]
    # Require at least 40% of text chars to be in this script
    if dominant_count < max(3, len(text) * 0.4):
        return None
    # Cyrillic is shared — defer to profile lang if it's a Cyrillic language
    if dominant == "ru" and profile_lang in _CYRILLIC_LANGS:
        return profile_lang
    return dominant


def _detect_lang(update: dict) -> str:
    # Step 1: get profile language from Telegram (user's app language)
    profile_lang = "en"
    text = ""
    for key in ("message", "edited_message", "callback_query"):
        entry = update.get(key, {})
        user = entry.get("from") or {}
        code = user.get("language_code", "")
        if code:
            profile_lang = code.split("-")[0].lower()
        # Also grab text to detect script
        if not text:
            text = (entry.get("text") or entry.get("caption") or "").strip()

    # Step 2: detect language from message script (overrides profile for unambiguous scripts)
    # Rationale: Telegram language_code = UI language of the app, not the message language.
    # A Georgian user writing in Georgian may have ru/en as their app language.
    script_lang = _detect_lang_from_script(text, profile_lang)
    if script_lang:
        return script_lang

    # Step 3: keyword detection for Latin-script languages that Telegram may
    # misreport (e.g. a Hausa speaker with app language set to English).
    # Only fires when script detection returned None (pure Latin text).
    if text:
        lower_text = text.lower()
        for lang_code, signals in _LATIN_LANG_SIGNALS:
            if any(sig in lower_text for sig in signals):
                return lang_code

    return profile_lang


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    # ── secret token check (optional — skip if not sent) ──
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

    # ── rate limiting ─────────────────────────────────────
    from cognition.response_synthesizer import get_system_message
    from security.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter and not await limiter.is_allowed(user_id):
        if chat_id:
            await _send_message(chat_id, get_system_message("rate_limited", lang))
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

    # ── message handling ──────────────────────────────────
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        try:
            result = await handle_message(
                update=update,
                update_type=update_type,
                user_id=user_id,
                user_balance=user_balance,
                lang=lang,
                supabase=supabase,
                redis=request.app.state.redis,
                hf_client=hf_client,
            )
        except Exception as exc:
            logger.error("handle_message crashed", extra={"error": str(exc)})
            if chat_id:
                await _send_message(
                    chat_id,
                    get_system_message("no_response", lang),
                )
            return {"ok": True}

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