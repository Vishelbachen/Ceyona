import logging
import re

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from lingua import Language, LanguageDetectorBuilder

from app.settings import settings
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.message_router import UpdateType, classify_update
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


async def _send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    if not text:
        return
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=10.0,
        )


def _top_up_keyboard(lang: str) -> dict:
    """
    Inline keyboard with a single "Top Up" button.
    Opens the TON wallet address in TON Space / any TON wallet via ton:// deeplink.
    Falls back to t.me/wallet deeplink for users without a TON app installed.
    """
    from app.settings import settings
    wallet = getattr(settings, "ton_wallet", None) or ""

    _BUTTON_LABELS: dict[str, str] = {
        "ru": "馃拵 袩芯锌芯谢薪懈褌褜 斜邪谢邪薪褋",
        "en": "馃拵 Top Up Balance",
        "de": "馃拵 Guthaben aufladen",
        "fr": "馃拵 Recharger le solde",
        "es": "馃拵 Recargar saldo",
        "pt": "馃拵 Recarregar saldo",
        "it": "馃拵 Ricarica il saldo",
        "tr": "馃拵 Bakiye y眉kle",
        "ar": "馃拵 卮丨賳 丕賱乇氐賷丿",
        "zh": "馃拵 鍏呭€间綑棰�",
        "ja": "馃拵 娈嬮珮銈掋儊銉ｃ兗銈�",
        "ko": "馃拵 鞛旍暋 於╈爠",
        "pl": "馃拵 Do艂aduj konto",
        "uk": "馃拵 袩芯锌芯胁薪懈褌懈 斜邪谢邪薪褋",
        "fa": "馃拵 卮丕乇跇 賲賵噩賵丿蹖",
        "nl": "馃拵 Saldo opladen",
        "sv": "馃拵 Fyll p氓 saldo",
        "no": "馃拵 Fyll p氓 saldo",
        "da": "馃拵 Opfyld saldo",
        "fi": "馃拵 Lataa saldo",
        "he": "馃拵 讟注讬谞转 讬转专讛",
        "ka": "馃拵 醿戓儛醿氠儛醿溼儭醿樶儭 醿ㄡ償醿曖儭醿斸儜醿�",
        "hy": "馃拵 諃铡沾铡宅謤榨宅 瞻铡辗斋站炸",
        "az": "馃拵 Balans谋 art谋r",
        "kk": "馃拵 袘邪谢邪薪褋褌褘 褌芯谢褌褘褉褍",
        "uz": "馃拵 Balansi to'ldirish",
        "mn": "馃拵 耶谢写褝谐写褝谢 薪褝屑褝褏",
        "sw": "馃拵 Ongeza salio",
        "am": "馃拵 釅€釄� 釄傖埑釅� 釄欋垕",
        "hi": "馃拵 啶啶侧啶傕じ 啶溹ぎ啶� 啶曕ぐ啷囙",
        "bn": "馃拵 唳唳唳侧唳ㄠ唳� 唳唳� 唳曕Π唰佮Θ",
        "ur": "馃拵 亘蹖賱賳爻 亘诰乇蹖诤",
        "id": "馃拵 Isi saldo",
        "ms": "馃拵 Tambah baki",
        "th": "馃拵 喙€喔曕复喔∴箑喔囙复喔�",
        "vi": "馃拵 N岷 s峄� d瓢",
        "bg": "馃拵 袟邪褉械写懈 斜邪谢邪薪褋",
        "hr": "馃拵 Napuni saldo",
        "sr": "馃拵 袧邪锌褍薪懈 褋褌邪褮械",
        "cs": "馃拵 Dob铆t kredit",
        "sk": "馃拵 Dobi钮 kredit",
        "ro": "馃拵 Re卯ncarc膬 soldul",
        "hu": "馃拵 Egyenleg felt枚lt茅se",
        "ha": "馃拵 茦ara ma'auni",
    }
    label = _BUTTON_LABELS.get(lang, _BUTTON_LABELS["en"])

    # ton:// deeplink opens any TON wallet app directly to the send screen
    url = f"ton://transfer/{wallet}" if wallet else "https://t.me/wallet"

    return {
        "inline_keyboard": [[
            {"text": label, "url": url}
        ]]
    }


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


# 鈹€鈹€鈹€ LINGUA ISO MAP 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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
    Language.GANDA:      "lg",   # Luganda 鈥� no bot support, falls back to profile
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
            # (e.g. GANDA/Luganda) 鈥� fall through to profile_lang below
        else:
            # lingua returned None: language is unrecognised (e.g. Inuktitut,
            # Greenlandic, invented text).  For very short inputs there is a
            # high risk of a wrong embedding-based intent match (e.g. MAPS),
            # so we flag this by returning profile_lang.  The downstream
            # intent classifier receives lang_uncertain=False (profile_lang
            # is still a valid lang code), but classify() will apply a higher
            # confidence threshold for short unrecognised texts 鈥� see
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

    logger.info("Incoming message", extra={"user_id": user_id, "lang": lang})

    # 鈹€鈹€ rate limiting 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    from cognition.response_synthesizer import get_system_message
    from security.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter and not await limiter.is_allowed(user_id):
        if chat_id:
            await _send_message(chat_id, get_system_message("rate_limited", lang))
        return {"ok": True}

    # 鈹€鈹€ balance 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    user_balance = 0.0
    try:
        from payments.access_controller import AccessController
        ac = AccessController(supabase)
        balance_result = await ac.get_balance(user_id)
        user_balance = balance_result.balance_usd
    except Exception as exc:
        logger.error("Balance fetch failed", extra={"error": str(exc)})

    # 鈹€鈹€ message handling 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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

        # 鈹€鈹€ billing 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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
            keyboard = (
                _top_up_keyboard(lang)
                if result.denied and result.deny_reason == "insufficient_balance"
                else None
            )
            await _send_message(chat_id, result.text, reply_markup=keyboard)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            bal_text = f"馃挵 Balance: ${user_balance:.2f}"
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