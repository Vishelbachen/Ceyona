from __future__ import annotations

import logging
import traceback

from contracts.shared_types import EPKDecision, Tier
from core.execution import (
    OrchestratorRequest,
    OrchestratorResult,
    UsageRecord,
    run,
)
from events.event_bus import event_bus
from events.event_types import (
    RequestCompletedEvent,
    UpdateReceivedEvent,
)
from transport.telegram.message_router import (
    UpdateType,
    extract_media_group_id,
    extract_message_id,
    extract_photo,
    extract_text,
    extract_voice,
    has_photo,
    has_voice,
)

logger = logging.getLogger(__name__)

_VISION_MODEL = "qwen/qwen3.6-27b"


async def handle_message(
    update: dict,
    update_type: UpdateType,
    user_id: int,
    user_balance: float,
    lang: str = "en",
    supabase=None,
    redis=None,
    hf_client=None,
    request_id: str = "",
    app_state=None,
    input_type: str = "text",
    vision_intent=None,
    is_vision: bool = False,
) -> OrchestratorResult:
    """
    Transport layer — pure I/O, no orchestration decisions.

    Responsibilities:
      - Parse Telegram Update (photo / voice / text)
      - Auth / media group buffering
      - ASR (voice → text)
      - Vision handler (photo → description)
      - TTS (text → audio, for voice responses)
      - Send: return OrchestratorResult to webhook

    Does NOT:
      - Run Safety Gates
      - Run multilingual normalization
      - Load/save history
      - Run retrieval
      - Classify complexity
      - Make any pipeline decisions
    """

    # ── update.received event ─────────────────────────────────────────────────
    try:
        await event_bus.publish(UpdateReceivedEvent(
            user_id=user_id,
            payload={
                "update_type": update_type.value if hasattr(update_type, "value") else str(update_type),
                "input_type": input_type,
                "request_id": request_id,
            },
        ))
    except Exception as _ev_exc:
        logger.debug("UpdateReceivedEvent publish failed", extra={"error": str(_ev_exc)})

    # ── photo handling ────────────────────────────────────────────────────────
    if has_photo(update):
        photo_meta = extract_photo(update)
        file_id    = photo_meta["file_id"]
        caption    = photo_meta.get("caption", "")
        group_id   = extract_media_group_id(update)
        message_id = extract_message_id(update)

        logger.info("Photo message received", extra={
            "user_id": user_id, "file_id": file_id[:20],
            "caption": caption[:50], "group_id": group_id,
        })

        # ── album: buffer in aggregator ───────────────────────────────────────
        if group_id and redis is not None:
            from transport.telegram.media_group_aggregator import (
                MediaGroupAggregator,
                MediaGroupItem,
            )
            scoped_group_id = f"{user_id}:{group_id}"
            aggregator: MediaGroupAggregator | None = getattr(app_state, "media_group_aggregator", None)
            if aggregator is None:
                logger.warning("MediaGroupAggregator not in app_state — creating ephemeral fallback",
                               extra={"user_id": user_id})
                async def _noop_callback(gid: str, items) -> None: pass
                aggregator = MediaGroupAggregator(redis, _noop_callback)
                await aggregator.start()
            item = MediaGroupItem(file_id=file_id, message_id=message_id, caption=caption, lang=lang)
            await aggregator.add(scoped_group_id, item)
            return OrchestratorResult(
                text="", tier=Tier.FAST, model="",
                epk_decision=EPKDecision.ALLOW,
                usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                                  rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
                denied=False, deny_reason="", lang=lang,
            )

        # ── single photo: vision handler ──────────────────────────────────────
        try:
            from transport.telegram.vision_handler import handle_vision
            vision_result = await handle_vision(file_id=file_id, caption=caption, lang=lang)
        except Exception as exc:
            logger.error(f"Vision handler crashed: {exc!r}\n{traceback.format_exc()}")
            from i18n.t import get_system_message
            return OrchestratorResult(
                text=get_system_message("vision_error", lang),
                tier=Tier.FAST, model="",
                epk_decision=EPKDecision.DENY,
                usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                                  rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
                denied=True, deny_reason="vision_error", lang=lang,
            )

        # ── CASE 1: vision fast-path ──────────────────────────────────────────
        if not vision_result.needs_pipeline:
            from payments.pricing_engine import vision_cost
            _vision_cost_usd = vision_cost(
                input_tokens=vision_result.vision_input_tokens,
                output_tokens=vision_result.vision_output_tokens,
            ) or 0.001
            if user_balance <= 0 or _vision_cost_usd > user_balance:
                logger.warning("Vision fast-path: balance insufficient",
                               extra={"user_id": user_id, "balance": user_balance, "cost": _vision_cost_usd})
                from i18n.t import get_system_message
                return OrchestratorResult(
                    text=get_system_message("insufficient_balance", lang),
                    tier=Tier.FAST, model="",
                    epk_decision=EPKDecision.DENY,
                    usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                                      rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
                    denied=True, deny_reason="insufficient_balance", lang=lang,
                )
            return OrchestratorResult(
                text=vision_result.text,
                tier=Tier.GENERAL, model=_VISION_MODEL,
                epk_decision=EPKDecision.ALLOW,
                usage=UsageRecord(
                    input_tokens=vision_result.vision_input_tokens,
                    output_tokens=vision_result.vision_output_tokens,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.GENERAL, embedding_type="large", llm_cost_usd=_vision_cost_usd,
                ),
                denied=False, deny_reason="", lang=lang,
            )

        # ── CASE 2: vision → pipeline ─────────────────────────────────────────
        logger.info("Vision pipeline-path: forwarding to orchestrator", extra={"user_id": user_id})
        update = dict(update)
        _vision_text_override  = vision_result.text
        _vision_intent_result  = vision_result.intent_result
        _vision_caption_for_history = caption if caption.strip() else "[фото]"

    # ── voice/audio handling (ASR → transcript) ───────────────────────────────
    _is_voice_input    = False
    _asr_audio_seconds = 0.0
    if not locals().get("_vision_text_override") and has_voice(update):
        voice_meta    = extract_voice(update)
        voice_file_id = voice_meta["file_id"] if voice_meta else None

        if voice_file_id:
            try:
                from app.settings import settings
                from external.speech_to_text import (
                    download_telegram_voice,
                    is_silent,
                    transcribe,
                )

                audio_bytes, filename = await download_telegram_voice(
                    file_id=voice_file_id, bot_token=settings.bot_token,
                )

                _voice_ext = filename.rsplit(".", 1)[-1].lower()
                if await is_silent(audio_bytes, source_ext=_voice_ext):
                    from i18n.t import get_system_message
                    return OrchestratorResult(
                        text=get_system_message("vad_silence", lang),
                        tier=Tier.FAST, model="",
                        epk_decision=EPKDecision.DENY,
                        usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                                          rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
                        denied=True, deny_reason="vad_silence", lang=lang,
                    )

                tr = await transcribe(audio_bytes=audio_bytes, filename=filename,
                                      lang=lang if lang != "en" else None)

                if not tr.success or not tr.text:
                    from i18n.t import get_system_message
                    return OrchestratorResult(
                        text=get_system_message("no_response", lang),
                        tier=Tier.FAST, model="",
                        epk_decision=EPKDecision.DENY,
                        usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                                          rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
                        denied=True, deny_reason="asr_failed", lang=lang,
                    )

                _is_voice_input    = True
                _asr_audio_seconds = tr.audio_seconds
                update = dict(update)
                update["_voice_transcript"] = tr.text
                logger.info("ASR complete", extra={
                    "user_id": user_id, "chars": len(tr.text), "seconds": tr.audio_seconds,
                })

            except Exception as exc:
                logger.error("Voice path crashed", extra={
                    "user_id": user_id, "error": str(exc), "exc_type": type(exc).__name__,
                })

    # ── text extraction ───────────────────────────────────────────────────────
    _vision_override = locals().get("_vision_text_override")
    _vision_caption  = locals().get("_vision_caption_for_history", "")
    if _vision_override and _vision_caption and _vision_caption != "[фото]":
        text = _vision_caption
        _vision_image_context = _vision_override
    else:
        text = _vision_override or update.get("_voice_transcript") or extract_text(update)
        _vision_image_context = None

    if not text:
        return OrchestratorResult(
            text="", tier=Tier.FAST, model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(input_tokens=0, output_tokens=0, embedding_tokens=0,
                              rerank_tokens=0, tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0),
            denied=True, deny_reason="empty_message", lang=lang,
        )

    # ── inject vision context into message ────────────────────────────────────
    _vic = locals().get("_vision_image_context")
    _vision_retrieved_ctx = ""
    if _vic:
        _vic_grounded = (
            "[VISUAL CONTEXT — answer only from what is described below. "
            "Do NOT infer, guess, or name platforms, apps, or entities "
            "unless their name is explicitly visible in the image.]\n" + _vic
        )
        _vision_retrieved_ctx = f"[Фото]\n{_vic_grounded}"

    # ── build orchestrator request (minimal) ──────────────────────────────────
    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        user_id=user_id,
        lang=lang,
        supabase=supabase,
        redis=redis,
        hf_client=hf_client,
        vision_intent=locals().get("_vision_intent_result") or vision_intent,
        skip_web_search=(
            locals().get("_vision_intent_result") is not None
            or vision_intent is not None
        ),
        is_vision=is_vision or (locals().get("_vision_text_override") is not None),
        request_id=request_id,
        input_type=input_type,
        vision_context=_vision_retrieved_ctx,
    )

    result = await run(request)

    # ── meta layer: reflection + memory_audit (async side-channel) ────────────
    try:
        from meta.memory_audit import MemorySnapshot, audit
        from meta.reflection import ReflectionInput, reflect

        ref_input = ReflectionInput(
            intent=result.intent or str(result.epk_decision),
            lang=lang,
            tier=str(result.tier),
            model=result.model or "",
            response_text=result.text or "",
            response_truncated=len(result.text or "") >= 4096,
            llm_cost_usd=result.usage.llm_cost_usd,
            was_degraded_mode=str(result.epk_decision) == "DEGRADED_MODE",
            safety_blocked=result.deny_reason == "safety_block",
            user_id=user_id,
        )
        report = reflect(ref_input)
        logger.info("Reflection", extra=report.to_dict())

        snap = MemorySnapshot(
            user_id=user_id,
            history_turn_count=0,  # orchestrator owns history — transport doesn't know count
            snapshot_available=True,
        )
        audit_report = audit(snap)
        if not audit_report.is_healthy():
            logger.warning("Memory audit", extra=audit_report.to_dict())

    except Exception as exc:
        logger.warning("Meta layer failed (non-critical)", extra={"error": str(exc)})

    # ── TTS (voice response) ──────────────────────────────────────────────────
    _tts_characters = 0
    _tts_model = ""
    if _is_voice_input and result.text and not result.denied:
        try:
            from external.text_to_speech import synthesize as tts_synthesize
            tts_result = await tts_synthesize(text=result.text, lang=lang)
            if tts_result.success:
                from dataclasses import replace
                result = replace(result, tts_audio_bytes=tts_result.audio_bytes)
                _tts_characters = tts_result.char_count
                _tts_model = tts_result.model_used
        except Exception as exc:
            logger.warning("TTS failed — returning text-only", extra={"error": str(exc)})

    # ── wire TTS billing fields ───────────────────────────────────────────────
    if _asr_audio_seconds or _tts_characters:
        from dataclasses import replace as _replace
        result = _replace(result,
            audio_seconds=_asr_audio_seconds,
            tts_characters=_tts_characters,
            tts_model=_tts_model,
        )

    # ── request.completed event ───────────────────────────────────────────────
    try:
        await event_bus.publish(RequestCompletedEvent(
            user_id=user_id,
            payload={
                "intent":         result.intent or str(result.epk_decision),
                "tier":           result.tier.value if result.tier else "",
                "model":          result.model or "",
                "total_cost_usd": result.usage.llm_cost_usd,
                "denied":         result.denied,
                "deny_reason":    result.deny_reason or "",
                "request_id":     request_id,
            },
        ))
    except Exception as _ev_exc:
        logger.debug("RequestCompletedEvent publish failed", extra={"error": str(_ev_exc)})

    return result