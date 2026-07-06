import asyncio
import logging
import time as _time

import httpx
from app.settings import settings
from events.event_bus import event_bus
from events.event_types import (
    AuthFailedEvent,
    BalanceExhaustedEvent,
    RequestDeniedEvent,
    SendToTelegramFailedEvent,
)
from fastapi import APIRouter, Header, HTTPException, Request, status
from lingua import Language, LanguageDetectorBuilder
from observability.metrics import gauge, increment
from observability.tracing import trace
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import dispatch_callback, parse_callback
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

_TELEGRAM_API = settings.telegram_proxy_url.rstrip("/") + "/tg/bot" + settings.bot_token

# Webhook secret is now a standalone secret (WEBHOOK_SECRET env var),
# independent of the bot token. Set the same value in HF Space secrets
# and Cloudflare Worker secrets.
_WEBHOOK_SECRET = settings.webhook_secret

# ─── Persistent outbound client ─────────────────────────────────────────────
# Single module-level client, reused for the lifetime of the process — same
# pattern already used by groq_client/hf_client (see llm/groq_client.py,
# llm/hf_client.py). A fresh `async with httpx.AsyncClient()` per call means a
# brand-new DNS resolution + TCP + TLS handshake every single time, which is
# exactly the phase that intermittently stalls on HF Space's egress network
# (see incident 2026-07-04: ConnectTimeout to the Cloudflare Worker proxy
# while every other outbound host in the same window succeeded). A pooled,
# keep-alive client means most calls reuse an already-established connection
# instead of repeating DNS+connect every time.
#
# limits: modest pool, since traffic to this one Worker host is not high
# volume — this is about connection reuse, not throughput.
_client = httpx.AsyncClient(
    timeout=httpx.Timeout(15.0, connect=10.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    follow_redirects=True,
)


async def aclose_telegram_client() -> None:
    """Call from app shutdown to release the pooled connections cleanly."""
    await _client.aclose()


# ─── Outbox Supabase handle ─────────────────────────────────────────────────
# ARCH-change 2026-07: outgoing Telegram messages are no longer sent via an
# HTTP call from this module (see _post_via_worker below) — they're written
# to Supabase's `outbox` table instead. This module-level handle is set once
# at startup from app.state.supabase (same object process_update() already
# receives as app_state.supabase), mirroring the _client singleton above.
# Set via set_outbox_supabase() in app/main.py's startup, right after
# bootstrap() returns.
_outbox_supabase = None


def set_outbox_supabase(supabase) -> None:
    global _outbox_supabase
    _outbox_supabase = supabase


# ─── Shared retry-with-backoff wrapper ──────────────────────────────────────
# Every outbound Telegram call (_send_message, _send_message_with_topup,
# _send_voice, _answer_callback) used to hand-roll its own try/except around
# a throwaway httpx.AsyncClient, with retry logic duplicated (or missing
# entirely) per function. One helper, one retry policy, one place to fix.
_RETRY_BACKOFF_S = (1.0, 3.0, 7.0)  # 3 retries → 4 attempts total


class _FakeResponse:
    """
    Minimal stand-in for httpx.Response, returned by _post_via_worker after
    a successful outbox insert. Callers only ever check .status_code and
    (on error) .text — see _send_message's `resp.status_code != 200` checks —
    so this is enough to keep every caller unmodified.
    """
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


async def _post_via_worker(
    path: str,
    *,
    chat_id: int | None = None,
    json: dict | None = None,
    data: dict | None = None,
    files: dict | None = None,
    timeout: float | None = None,
) -> httpx.Response | None:
    """
    ARCH-change 2026-07: HF no longer makes an outbound HTTP call to the
    Cloudflare Worker (or to api.telegram.org) at all — not even indirectly.
    That outbound call was the confirmed failure point (see incident
    2026-07-04: ConnectTimeout on HF's egress to workers.dev while every
    other outbound host, including Supabase, succeeded in the same window).

    Instead, this function INSERTs the outgoing message into Supabase's
    `outbox` table. A separate, always-on process outside HF (the same
    Cloudflare Worker, repurposed — see ceyona-worker/worker.js outbox
    poller) reads new `outbox` rows and performs the actual Telegram API
    call. HF's only outbound dependency for sending a reply is now
    Supabase, which is already the one host that has never shown a
    ConnectTimeout in production logs.

    `files` (voice messages) are base64-encoded into the payload column —
    Supabase REST/PostgREST has no native multipart support, and voice
    volume is low enough that base64 overhead doesn't matter here.

    Returns a _FakeResponse(200) on successful insert (callers only check
    .status_code), or None if the insert itself failed (e.g. Supabase is
    down) — same contract as before, so every caller (_send_message,
    _send_voice, _answer_callback, …) needs no changes.
    """
    import base64

    row: dict = {
        "path": path,
        "chat_id": chat_id,
        "status": "pending",
        "created_at": _now_iso(),
    }
    if json is not None:
        row["json_body"] = json
    if data is not None:
        row["form_data"] = data
    if files is not None:
        encoded = {}
        for field, value in files.items():
            filename, fileobj, content_type = value
            raw = fileobj.read() if hasattr(fileobj, "read") else fileobj
            encoded[field] = {
                "filename": filename,
                "content_type": content_type,
                "data_b64": base64.b64encode(raw).decode("ascii"),
            }
        row["files_b64"] = encoded

    if _outbox_supabase is None:
        logger.error(
            "_post_via_worker: outbox Supabase client not initialised — "
            "did app startup call set_outbox_supabase(app.state.supabase)?",
            extra={"chat_id": chat_id, "path": path},
        )
        return None

    try:
        result = _outbox_supabase.table("outbox").insert(row).execute()
        if not result.data:
            raise RuntimeError("outbox insert returned no data")
        logger.info(
            "_post_via_worker: enqueued to outbox",
            extra={"chat_id": chat_id, "path": path, "outbox_id": result.data[0].get("id")},
        )
        return _FakeResponse(200)
    except Exception as exc:
        logger.error(
            "_post_via_worker: outbox insert failed",
            extra={"chat_id": chat_id, "path": path, "error": repr(exc)},
        )
        try:
            await event_bus.publish(SendToTelegramFailedEvent(
                user_id=chat_id,
                payload={"path": path, "error": repr(exc)},
            ))
        except Exception:
            pass
        return None


def _now_iso() -> str:
    """Client-side timestamp — see queue_consumer.py's identical helper for why
    (PostgREST doesn't evaluate SQL now() from a JSON body)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def _send_message(chat_id: int, text: str) -> None:
    """
    KNOWN BEHAVIOR CHANGE (ARCH-change 2026-07, outbox): the Markdown-parse-
    error fallback below used to fire for real, because _post_via_worker
    returned Telegram's actual response (e.g. 400 on bad Markdown), synchronously,
    to this function. Now _post_via_worker only reports whether the outbox
    INSERT succeeded — it returns 200 the moment Supabase accepts the row,
    long before the Worker has actually tried Telegram. So resp.status_code
    is essentially always 200 here, and the "retry without Markdown" branch
    below will not trigger anymore. Markdown-parse failures now have to be
    handled on the Worker side (which does see Telegram's real response) —
    see ceyona-worker/worker.js's outbox poller. Left the two-attempt shape
    in place rather than ripping it out, since it's harmless dead code on
    the HF side and documents the gap for whoever wires up the Worker-side
    equivalent.
    """
    logger.info("_send_message called", extra={"chat_id": chat_id, "text_len": len(text) if text else 0})
    if not text:
        return

    resp = await _post_via_worker(
        "/sendMessage",
        chat_id=chat_id,
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
    )
    if resp is not None and resp.status_code == 200:
        return
    if resp is not None:
        logger.error(
            "sendMessage outbox-insert failed — retrying once",
            extra={"chat_id": chat_id, "status": resp.status_code, "body": resp.text[:200]},
        )

    resp = await _post_via_worker(
        "/sendMessage",
        chat_id=chat_id,
        json={"chat_id": chat_id, "text": text},
    )
    if resp is not None and resp.status_code != 200:
        logger.error(
            "sendMessage retry also failed",
            extra={"chat_id": chat_id, "status": resp.status_code, "body": resp.text[:200]},
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

    await _post_via_worker(
        "/sendMessage",
        chat_id=chat_id,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        },
    )


async def _send_voice(chat_id: int, audio_bytes: bytes, caption: str = "") -> bool:
    """
    Send a voice message via Telegram sendVoice.
    Returns True on success, False on failure.
    Falls back gracefully — caller sends text if this returns False.
    """
    import io
    resp = await _post_via_worker(
        "/sendVoice",
        chat_id=chat_id,
        data={"chat_id": chat_id, "caption": caption},
        files={"voice": ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg")},
        timeout=30.0,
    )
    return resp is not None and resp.status_code == 200


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    await _post_via_worker(
        "/answerCallbackQuery",
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
    if not x_telegram_bot_api_secret_token or \
       not verify_webhook_secret(x_telegram_bot_api_secret_token, _WEBHOOK_SECRET):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        update: dict = await request.json()
    except Exception as exc:
        logger.error("Failed to parse update JSON", extra={"error": str(exc)})
        return {"ok": True}

    return await process_update(update, request.app.state)


async def process_update(update: dict, app_state) -> dict:
    """
    Транспортно-независимая обработка одного Telegram update.

    Раньше вся эта логика жила прямо в HTTP-роуте telegram_webhook() и была
    завязана на FastAPI Request (request.app.state.*). Теперь она вынесена
    отдельно, чтобы её мог вызывать не только HTTP-роут, но и фоновый
    consumer очереди (см. queue/consumer.py), который вычитывает апдейты
    из Supabase (pending_updates) вместо того, чтобы ждать их через HTTP —
    это убирает зависимость от синхронного forward со стороны Cloudflare
    Worker и связанный с ним риск таймаута.

    app_state — тот же объект, что обычно доступен как request.app.state
    (со свойствами .supabase, .hf_client, .redis), передаётся явно, чтобы
    эта функция не зависела от наличия HTTP-запроса.
    """
    update_type = classify_update(update)

    if update_type == UpdateType.UNKNOWN:
        return {"ok": True}

    auth = verify_update(update)
    if not auth.allowed:
        logger.warning("Rejected update", extra={"reason": auth.reason})
        try:
            await event_bus.publish(AuthFailedEvent(
                user_id=None,
                payload={"reason": auth.reason},
            ))
        except Exception:
            pass
        return {"ok": True}

    chat_id = _get_chat_id(update)
    logger.info("chat_id resolved", extra={"chat_id": chat_id, "update_keys": list(update.keys())})
    user_id = auth.user_id
    lang = _detect_lang(update)
    supabase = app_state.supabase
    hf_client = app_state.hf_client

    # Fix §10.4: generate request_id for full pipeline log correlation.
    # Format: "{update_id}:{user_id}" — unique per Telegram update.
    _update_id = str(update.get("update_id", ""))
    request_id = f"{_update_id}:{user_id}" if _update_id else str(user_id)
    logger.info("Incoming message", extra={"request_id": request_id, "user_id": user_id, "lang": lang})

    # ── rate limiting ─────────────────────────────────────────────────────────
    from i18n.t import get_system_message
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
    # The entire block is wrapped in try/except: if _send_message_with_topup or
    # _send_message raises (network error, Telegram timeout), we log and return
    # cleanly instead of letting the exception propagate to FastAPI and causing
    # Telegram to retry the update indefinitely.
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE) and chat_id:
        raw_text = extract_text(update).strip()
        try:
            if raw_text.startswith("/balance"):
                bal_text = f"💰 Balance: ${user_balance:.4f}"
                await _send_message_with_topup(chat_id, bal_text, lang)
                return {"ok": True}
            if raw_text.startswith("/start"):
                await _send_message(chat_id, get_system_message("help_display", lang))
                return {"ok": True}
            if raw_text.startswith("/help"):
                await _send_message(chat_id, get_system_message("help_display", lang))
                return {"ok": True}

            # ── /clear — Mode A: session reset (conversation history only) ────────
            # Clears conversation_history from Supabase.
            # Long-term memory (SupabaseStore) is intentionally preserved —
            # the user wants a fresh dialogue, not to lose personalisation.
            # Cache is not touched: it is infrastructure, not user identity.
            if raw_text.startswith("/clear"):
                if supabase is not None:
                    from memory.conversation_history import ConversationHistory
                    history_store = ConversationHistory(supabase)
                    await history_store.clear(user_id)
                await _send_message(chat_id, get_system_message("session_cleared", lang))
                return {"ok": True}

            # ── /reset_memory — Mode B: full memory wipe (irreversible) ──────────
            # Two-step confirmation: first call shows warning, second with "confirm"
            # executes the wipe. Both conversation_history and long-term memory
            # (SupabaseStore) are deleted. QueryCache is also cleared — it is the
            # only user-scoped cache (keyed by user_id hash).
            # EmbeddingCache and RerankCache are NOT touched: they are global
            # infrastructure caches with no user identity, not memory layers.
            if raw_text.startswith("/reset_memory"):
                confirmed = "confirm" in raw_text
                if not confirmed:
                    await _send_message(chat_id, get_system_message("memory_reset_confirm", lang))
                    return {"ok": True}
                # Confirmed — execute full wipe
                if supabase is not None:
                    from memory.conversation_history import ConversationHistory
                    from memory.supabase_store import SupabaseStore
                    await ConversationHistory(supabase).clear(user_id)
                    await SupabaseStore(supabase).delete_by_user(str(user_id))
                # QueryCache: clear user-scoped retrieval cache from Redis
                if app_state.redis is not None:
                    from retrieval.cache.query_cache import QueryCache
                    qcache = QueryCache(app_state.redis)
                    await qcache.delete_by_user(str(user_id))
                logger.info("Full memory reset executed", extra={"user_id": user_id})
                await _send_message(chat_id, get_system_message("memory_reset_done", lang))
                return {"ok": True}

        except Exception as exc:
            logger.error(
                "Command handler failed",
                extra={"cmd": raw_text[:30], "error": repr(exc)},
            )
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
                    redis=app_state.redis,
                    hf_client=hf_client,
                    request_id=request_id,
                    app_state=app_state,
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
        # Bill whenever there is any cost — LLM or Safety Gate tokens.
        # DENY requests may carry Safety Gate tokens (e.g. safety_gate_pass1 voice
        # block) and MUST be billed for them per economic.md §2.
        # Guard: skip only when there is genuinely nothing to bill.
        _has_safety_tokens = (
            result.safety_pass1_tokens
            or result.safety_pass2_tokens
            or result.safety_safeguard_tokens
            or result.safety_safeguard_output_tokens
        )
        _has_ml_tokens = bool(result.multilingual_input_tokens or result.multilingual_output_tokens)
        _total_cost_usd = result.usage.llm_cost_usd  # updated after billing block with full cost
        if result.usage.llm_cost_usd > 0 or _has_safety_tokens or _has_ml_tokens:
            try:
                from core.kernel.cost_model import (
                    actual_asr_cost,
                    actual_compound_cost,
                    actual_compound_cost_from_breakdown,
                    actual_multilingual_cost,
                    actual_safety_cost,
                    actual_tts_cost,
                )
                from payments.access_controller import AccessController
                from payments.usage_meter import UsageEntry, UsageMeter

                # Compute actual Safety Gate cost from real token counts (Variant C).
                # Safety tokens are captured in update_handler after both passes complete
                # and wired onto result via dataclasses.replace(). They are NOT included
                # in result.usage.llm_cost_usd (orchestrator runs between the two passes).
                # On DENY paths where gate blocked (e.g. voice pass1), tokens are
                # carried directly on OrchestratorResult — still billed here.
                safety_cost = actual_safety_cost(
                    pass1_tokens=result.safety_pass1_tokens,
                    pass2_tokens=result.safety_pass2_tokens,
                    safeguard_tokens=result.safety_safeguard_tokens,
                    safeguard_output_tokens=result.safety_safeguard_output_tokens,
                )

                # Compute actual multilingual_preprocessor cost (economic.md §2).
                # Runs inside orchestrator.run() pipeline — not included in
                # result.usage.llm_cost_usd on ALLOW/DEGRADED paths (only on HEAVY).
                # model: "allam-2-7b" ($0.075/$0.30) | "qwen/qwen3.6-27b" ($0.60/$3.00) | "passthrough" ($0)
                # On HEAVY path _run_heavy() already billed these — guard against double-billing.
                _ml_cost = 0.0
                if result.multilingual_input_tokens or result.multilingual_output_tokens:
                    from contracts.shared_types import (
                        EPKDecision as _EPKDecision,  # BUG-1 fix: contracts.orchestrator does not exist
                    )

                    # _run_heavy() bakes multilingual cost into llm_cost_usd — skip to avoid double-billing
                    if result.epk_decision != _EPKDecision.HEAVY_REQUIRED:
                        _ml_cost = actual_multilingual_cost(
                            input_tokens=result.multilingual_input_tokens,
                            output_tokens=result.multilingual_output_tokens,
                            model=result.multilingual_model,
                        )

                # safety_agent and lc_transformer costs are already baked into
                # result.usage.llm_cost_usd by _run_heavy(). No double-billing.

                # ── Speech billing (ASR + TTS) ─────────────────────────────
                # audio_seconds → Whisper ($/hour), tts_characters → Orpheus ($/1M chars).
                # These are NOT in llm_cost_usd — computed separately here.
                # economic.md §1.4 / revenue-leak fix Jun 2026.
                _asr_cost = actual_asr_cost(
                    audio_seconds=result.audio_seconds,
                ) if result.audio_seconds else 0.0
                _tts_cost = actual_tts_cost(
                    tts_characters=result.tts_characters,
                    model=result.tts_model or "canopylabs/orpheus-v1-english",
                ) if result.tts_characters else 0.0

                # ── Compound model billing ─────────────────────────────────
                # compound / compound-mini use passthrough pricing (Groq docs, Jun 2026).
                # Preferred path: use usage_breakdown from Groq API for exact per-model billing.
                # Fallback: dominant-model rate approximation when breakdown is absent.
                # In both cases, subtract the FAST-tier proxy already baked into llm_cost_usd
                # and add the correct compound cost. economic.md §1.3 / BUG-01+BUG-02 fix.
                _compound_cost_delta = 0.0
                _COMPOUND_MODELS = {"groq/compound-mini", "groq/compound"}
                if result.resolved_model in _COMPOUND_MODELS:
                    from contracts.shared_types import Tier
                    from core.kernel.cost_model import (
                        MODEL_RATES,
                        actual_compound_cost_from_breakdown,
                    )
                    _fast_rates = MODEL_RATES[Tier.FAST]
                    _fast_proxy = (
                        result.usage.input_tokens * _fast_rates["input"]
                        + result.usage.output_tokens * _fast_rates["output"]
                    ) / 1_000_000

                    _breakdown = getattr(result, "compound_breakdown", [])
                    if _breakdown:
                        # Exact billing: per-model rates from Groq usage_breakdown
                        _compound_actual = actual_compound_cost_from_breakdown(_breakdown)
                    else:
                        # Fallback: dominant-model approximation
                        _compound_actual = actual_compound_cost(
                            input_tokens=result.usage.input_tokens,
                            output_tokens=result.usage.output_tokens,
                            model=result.resolved_model,
                        )
                    _compound_cost_delta = _compound_actual - _fast_proxy

                # ── SAFETY-6 Revision pass billing ────────────────────────
                # Revision is a separate Groq LLM call — billed at primary tier rates.
                # Tokens are NOT in llm_cost_usd (that tracks primary only).
                # economic.md §2: every model call MUST be billed.
                # _run_heavy() path: revision uses HEAVY (gpt-oss-120b) rates.
                # ALLOW/consensus path: revision uses primary model rates for that tier.
                # Both map to result.usage.tier — safe approximation (same model, same tier).
                _revision_cost = 0.0
                if result.revision_input_tokens or result.revision_output_tokens:
                    from contracts.shared_types import Tier as _Tier
                    from core.kernel.cost_model import MODEL_RATES as _MODEL_RATES
                    _rev_tier = result.usage.tier if result.usage.tier else _Tier.GENERAL
                    _rev_rates = _MODEL_RATES[_rev_tier]
                    _revision_cost = (
                        result.revision_input_tokens * _rev_rates["input"]
                        + result.revision_output_tokens * _rev_rates["output"]
                    ) / 1_000_000

                total_cost_usd = (
                    result.usage.llm_cost_usd
                    + safety_cost
                    + _ml_cost
                    + _asr_cost
                    + _tts_cost
                    + _compound_cost_delta
                    + _revision_cost
                )
                _total_cost_usd = total_cost_usd  # expose to outer scope for logging

                ac = AccessController(supabase)
                await ac.deduct(user_id, total_cost_usd)

                meter = UsageMeter(supabase)
                billed = meter.compute_billed(total_cost_usd)
                await meter.record(UsageEntry(
                    user_id=user_id,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    embedding_tokens=result.usage.embedding_tokens,
                    rerank_tokens=result.usage.rerank_tokens,
                    tier=result.usage.tier,
                    embedding_type=result.usage.embedding_type,
                    raw_cost_usd=total_cost_usd,
                    billed_cost_usd=billed,
                    model=result.model,
                    resolved_model=result.resolved_model,
                    lang=result.lang,
                    intent=result.intent,
                    audio_seconds=result.audio_seconds,
                    tts_characters=result.tts_characters,
                    tool_calls=result.tool_calls,
                    safety_pass1_tokens=result.safety_pass1_tokens,
                    safety_pass2_tokens=result.safety_pass2_tokens,
                    safety_safeguard_tokens=result.safety_safeguard_tokens,
                    safety_safeguard_output_tokens=result.safety_safeguard_output_tokens,
                    safety_agent_input_tokens=result.safety_agent_input_tokens,
                    safety_agent_output_tokens=result.safety_agent_output_tokens,
                    revision_input_tokens=result.revision_input_tokens,
                    revision_output_tokens=result.revision_output_tokens,
                    multilingual_input_tokens=result.multilingual_input_tokens,
                    multilingual_output_tokens=result.multilingual_output_tokens,
                    multilingual_model=result.multilingual_model,
                    lc_transformer_input_tokens=result.lc_transformer_input_tokens,
                    lc_transformer_output_tokens=result.lc_transformer_output_tokens,
                ))
            except Exception as exc:
                logger.error("Billing failed", extra={"error": str(exc)})

        # Track denied/allowed outcomes + publish domain events
        if result.denied:
            increment(f"webhook.denied.{result.deny_reason or 'unknown'}")
            # Publish domain event — non-blocking, fire-and-forget via asyncio.create_task()
            try:
                if result.deny_reason == "insufficient_balance":
                    await event_bus.publish(BalanceExhaustedEvent(
                        user_id=user_id,
                        payload={
                            "deny_reason": result.deny_reason,
                            "intent": result.intent or str(result.epk_decision),
                        },
                    ))
                else:
                    await event_bus.publish(RequestDeniedEvent(
                        user_id=user_id,
                        payload={
                            "deny_reason": result.deny_reason or "unknown",
                            "intent": result.intent or str(result.epk_decision),
                        },
                    ))
            except Exception as _ev_exc:
                logger.debug("Deny event publish failed", extra={"error": str(_ev_exc)})
        else:
            increment("webhook.allowed")
        logger.info("Request complete", extra={
            "request_id": request_id,
            "denied":     result.denied,
            "tier":       result.tier.value if result.tier else "",
            "model":      result.model,
            "intent":     result.intent,
            "total_cost_usd": f"{_total_cost_usd:.6f}",
        })

        if chat_id:
            # Low balance warning — at most once per 24 h per user (Redis dedup).
            # Key format and TTL are canonical in infra/redis_keys.py.
            try:
                from infra import redis_keys
                from payments.access_controller import AccessController
                ac2 = AccessController(supabase)
                fresh_balance = await ac2.get_balance(user_id)
                if 0 < fresh_balance.balance_usd < 0.05:
                    _redis = app_state.redis
                    if _redis is not None:
                        _sent = await _redis.set(
                            redis_keys.low_balance_warning(user_id),
                            "1",
                            ex=redis_keys.LOW_BALANCE_WARNING_TTL,
                            nx=True,
                        )
                        if _sent:
                            from i18n.t import t as _t
                            await _send_message_with_topup(
                                chat_id, _t("low_balance_warning", lang), lang
                            )
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
            elif result.deny_reason == "insufficient_balance":
                # Always show topup button on balance denial — user needs a clear action path.
                await _send_message_with_topup(chat_id, result.text, lang)
            else:
                await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)
        await dispatch_callback(
            ctx=ctx,
            chat_id=chat_id,
            user_balance=user_balance,
            lang=lang,
            send_message=_send_message,
            send_message_with_topup=_send_message_with_topup,
            answer_callback=_answer_callback,
        )

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