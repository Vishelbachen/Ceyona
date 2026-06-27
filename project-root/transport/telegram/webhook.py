import logging

import httpx
from app.settings import settings
from fastapi import APIRouter, Header, HTTPException, Request, status
from lingua import Language, LanguageDetectorBuilder
from observability.metrics import gauge, increment
from observability.tracing import trace
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.message_router import UpdateType, classify_update, extract_text
from transport.telegram.update_handler import handle_message
from events.event_bus import event_bus
from events.event_types import AuthFailedEvent, BalanceExhaustedEvent, RequestDeniedEvent

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

# Apps Script proxy URL for sending messages (HF blocks direct Cloudflare Worker calls)
_APPS_SCRIPT_URL = settings.apps_script_url

# Webhook secret is now a standalone secret (WEBHOOK_SECRET env var),
# independent of the bot token. Set the same value in HF Space secrets
# and Cloudflare Worker secrets.
_WEBHOOK_SECRET = settings.webhook_secret


async def _send_message(chat_id: int, text: str) -> None:
    logger.info("_send_message called", extra={"chat_id": chat_id, "text_len": len(text) if text else 0})
    if not text:
        return

    async def _attempt(txt: str, parse_mode: str | None) -> tuple[int, str]:
        """Send message via Apps Script → Telegram API."""
        payload: dict = {"method": "sendMessage", "params": {"chat_id": chat_id, "text": txt}}
        if parse_mode:
            payload["params"]["parse_mode"] = parse_mode
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            logger.info("_attempt sending")
            import json as _json
            resp = await client.get(
                _APPS_SCRIPT_URL,
                params={"method": payload["method"], "params": _json.dumps(payload["params"])},
            )
            logger.info("_attempt response", extra={"status": resp.status_code, "body": resp.text[:200]})
            return resp.status_code, resp.text

    # Attempt 1: with Markdown
    try:
        status, body = await _attempt(text, "Markdown")
        if status == 200:
            return
        logger.error(
            "sendMessage failed — retrying without Markdown",
            extra={"chat_id": chat_id, "status": status, "body": body[:200]},
        )
    except Exception as exc:
        logger.error("sendMessage network error — retrying without Markdown", extra={"chat_id": chat_id, "error": repr(exc)})

    # Attempt 2: plain text, no parse_mode
    try:
        status, body = await _attempt(text, None)
        if status != 200:
            logger.error(
                "sendMessage retry also failed",
                extra={"chat_id": chat_id, "status": status, "body": body[:200]},
            )
    except Exception as exc:
        logger.error("sendMessage retry exception", extra={"chat_id": chat_id, "error": repr(exc)})


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

    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
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
    if not x_telegram_bot_api_secret_token or \
       not verify_webhook_secret(x_telegram_bot_api_secret_token, _WEBHOOK_SECRET):
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
    supabase = request.app.state.supabase
    hf_client = request.app.state.hf_client

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
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE) and chat_id:
        raw_text = extract_text(update).strip()
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
            if request.app.state.redis is not None:
                from retrieval.cache.query_cache import QueryCache
                qcache = QueryCache(request.app.state.redis)
                await qcache.delete_by_user(str(user_id))
            logger.info("Full memory reset executed", extra={"user_id": user_id})
            await _send_message(chat_id, get_system_message("memory_reset_done", lang))
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
                    app_state=request.app.state,
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
                # Runs in update_handler BEFORE orchestrator — not included in
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
            # Low balance warning — show topup button when balance drops below $0.05
            try:
                from payments.access_controller import AccessController
                ac2 = AccessController(supabase)
                fresh_balance = await ac2.get_balance(user_id)
                if 0 < fresh_balance.balance_usd < 0.05:
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
            elif result.deny_reason == "insufficient_balance":
                # Always show topup button on balance denial — user needs a clear action path.
                await _send_message_with_topup(chat_id, result.text, lang)
            else:
                await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            bal_text = f"💰 Balance: ${user_balance:.2f}"
            await _answer_callback(ctx.callback_query_id, bal_text)
        elif ctx.action == CallbackAction.TOPUP:
            # Acknowledge the button press immediately (removes spinner)
            await _answer_callback(ctx.callback_query_id)
            # Send TON wallet address as a message the user can act on
            import secrets

            from app.settings import settings as _s
            wallet = _s.ton_wallet
            if wallet:
                # Generate a random suffix to prevent memo-guessing attacks:
                # attacker knowing someone's Telegram ID cannot credit their account
                # by sending TON with just the ID as memo.
                _memo_suffix = secrets.token_hex(4)  # e.g. "a3f9c2b1"
                _memo = f"{user_id}_{_memo_suffix}"
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
                await _send_message(chat_id, topup_text)
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