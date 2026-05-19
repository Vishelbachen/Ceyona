from __future__ import annotations

import asyncio
import logging
import traceback

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, UsageRecord, run
from transport.telegram.message_router import (
    UpdateType, extract_text, extract_photo, has_photo,
    has_voice, extract_voice,
)

logger = logging.getLogger(__name__)

_VISION_MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
_NO_SEARCH_INTENTS = {"creative", "conversation", "emotional", "code", "math"}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_history_tokens(history: list[dict] | None) -> int:
    if not history:
        return 0
    return sum(_estimate_tokens(t.get("content", "")) for t in history)


def _classify_complexity(text: str) -> Complexity:
    has_code = "```" in text or "    " in text
    has_json = "{" in text and "}" in text
    length   = len(text)
    if has_code and has_json:
        return Complexity.CRITICAL
    if has_code or has_json:
        return Complexity.HIGH
    if length > 500:
        return Complexity.MEDIUM
    return Complexity.LOW


async def handle_message(
    update: dict,
    update_type: UpdateType,
    user_id: int,
    user_balance: float,
    lang: str = "en",
    supabase=None,
    redis=None,
    hf_client=None,
) -> OrchestratorResult:

    # ── photo handling ────────────────────────────────────────────────────────
    if has_photo(update):
        photo_meta = extract_photo(update)
        file_id    = photo_meta["file_id"]
        caption    = photo_meta.get("caption", "")

        logger.info("Photo message received", extra={
            "user_id": user_id,
            "file_id": file_id[:20],
            "caption": caption[:50],
        })

        # Safety Gate Pass 1 on caption (photo text)
        if caption:
            try:
                from security.safety_gate import check_pass1, GateVerdict
                gate1 = await asyncio.wait_for(check_pass1(caption), timeout=8.0)
                if gate1.verdict == GateVerdict.DENY:
                    from cognition.response_synthesizer import get_system_message
                    return OrchestratorResult(
                        text=get_system_message("safety_block", lang),
                        tier=Tier.FAST, model=gate1.model_used,
                        epk_decision=EPKDecision.DENY,
                        usage=UsageRecord(
                            input_tokens=0, output_tokens=0,
                            embedding_tokens=0, rerank_tokens=0,
                            tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                        ),
                        denied=True, deny_reason="safety_gate_pass1", lang=lang,
                    )
            except asyncio.TimeoutError:
                logger.warning("Safety Gate Pass 1 (photo) timeout — skipping", extra={"user_id": user_id})
            except Exception as exc:
                logger.error("Safety Gate Pass 1 (photo) crashed — skipping", extra={"error": str(exc)})

        try:
            from transport.telegram.vision_handler import handle_vision
            vision_result = await handle_vision(
                file_id=file_id,
                caption=caption,
                lang=lang,
            )
        except Exception as exc:
            logger.error(f"Vision handler crashed: {exc!r}\n{traceback.format_exc()}")
            from cognition.response_synthesizer import get_system_message
            return OrchestratorResult(
                text=get_system_message("vision_error", lang),
                tier=Tier.FAST,
                model="",
                epk_decision=EPKDecision.DENY,
                usage=UsageRecord(
                    input_tokens=0, output_tokens=0,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                ),
                denied=True,
                deny_reason="vision_error",
                lang=lang,
            )

        # ── CASE 1: descriptive — direct response, no pipeline ────────────────
        if not vision_result.needs_pipeline:
            logger.info("Vision fast-path: direct response", extra={"user_id": user_id})
            return OrchestratorResult(
                text=vision_result.text,
                tier=Tier.GENERAL,
                model=_VISION_MODEL,
                epk_decision=EPKDecision.ALLOW,
                usage=UsageRecord(
                    input_tokens=_estimate_tokens(caption) + 500,
                    output_tokens=_estimate_tokens(vision_result.text),
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.GENERAL, embedding_type="large", cost_usd=0.001,
                ),
                denied=False,
                deny_reason="",
                lang=lang,
            )

        # ── CASE 2: analytical — forward into main pipeline ───────────────────
        logger.info("Vision pipeline-path: forwarding to orchestrator", extra={"user_id": user_id})
        update = dict(update)
        _vision_text_override  = vision_result.text
        _vision_intent_result  = vision_result.intent_result

    # ── voice/audio handling (ASR → transcript → pipeline) ───────────────────
    _is_voice_input    = False
    _asr_audio_seconds = 0.0
    if not locals().get("_vision_text_override") and has_voice(update):
        voice_meta    = extract_voice(update)
        voice_file_id = voice_meta["file_id"] if voice_meta else None

        if voice_file_id:
            try:
                from security.safety_gate import check_pass1
                from external.speech_to_text import download_telegram_voice, transcribe
                from app.settings import settings

                audio_bytes, filename = await download_telegram_voice(
                    file_id=voice_file_id,
                    bot_token=settings.bot_token,
                )

                tr = await transcribe(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    lang=lang if lang != "en" else None,
                )

                if not tr.success or not tr.text:
                    logger.warning("ASR failed", extra={"user_id": user_id})
                    from cognition.response_synthesizer import get_system_message
                    return OrchestratorResult(
                        text=get_system_message("no_response", lang),
                        tier=Tier.FAST, model="",
                        epk_decision=EPKDecision.DENY,
                        usage=UsageRecord(
                            input_tokens=0, output_tokens=0,
                            embedding_tokens=0, rerank_tokens=0,
                            tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                        ),
                        denied=True, deny_reason="asr_failed", lang=lang,
                    )

                # Safety Gate Pass 1 on transcript text
                try:
                    gate1 = await asyncio.wait_for(check_pass1(tr.text), timeout=8.0)
                    if not gate1.safe:
                        from cognition.response_synthesizer import get_system_message
                        return OrchestratorResult(
                            text=get_system_message("safety_block", lang),
                            tier=Tier.FAST, model="",
                            epk_decision=EPKDecision.DENY,
                            usage=UsageRecord(
                                input_tokens=0, output_tokens=0,
                                embedding_tokens=0, rerank_tokens=0,
                                tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                            ),
                            denied=True, deny_reason="safety_gate_pass1", lang=lang,
                        )
                except asyncio.TimeoutError:
                    logger.warning("Safety Gate Pass 1 (voice) timeout — skipping", extra={"user_id": user_id})

                _is_voice_input    = True
                _asr_audio_seconds = tr.audio_seconds
                update = dict(update)
                update["_voice_transcript"] = tr.text
                logger.info(
                    "ASR complete — forwarding to pipeline",
                    extra={"user_id": user_id, "chars": len(tr.text), "seconds": tr.audio_seconds},
                )

            except asyncio.TimeoutError:
                pass  # already handled above
            except Exception as exc:
                logger.error("Voice path crashed", extra={"user_id": user_id, "error": str(exc)})

    # ── text extraction ───────────────────────────────────────────────────────
    text = (
        locals().get("_vision_text_override")
        or update.get("_voice_transcript")
        or extract_text(update)
    )

    if not text:
        logger.info("Empty text update ignored", extra={"user_id": user_id})
        return OrchestratorResult(
            text="",
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=0, output_tokens=0,
                embedding_tokens=0, rerank_tokens=0,
                tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
            ),
            denied=True,
            deny_reason="empty_message",
            lang=lang,
        )

    # ── Safety Gate Pass 1 — fast rejection (BEFORE Feature Extraction) ───────
    try:
        from security.safety_gate import check_pass1, GateVerdict
        gate1 = await asyncio.wait_for(check_pass1(text), timeout=8.0)
        if gate1.verdict == GateVerdict.DENY:
            logger.warning("Safety Gate Pass 1 blocked message", extra={"user_id": user_id})
            from cognition.response_synthesizer import get_system_message
            return OrchestratorResult(
                text=get_system_message("safety_block", lang),
                tier=Tier.FAST, model=gate1.model_used,
                epk_decision=EPKDecision.DENY,
                usage=UsageRecord(
                    input_tokens=0, output_tokens=0,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                ),
                denied=True, deny_reason="safety_gate_pass1", lang=lang,
            )
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 1 timeout — skipping", extra={"user_id": user_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 1 crashed — skipping", extra={"error": str(exc)})

    complexity = _classify_complexity(text)

    # ── multilingual normalization ─────────────────────────────────────────────
    # Normalize non-Latin scripts (Arabic via allam-2-7b, others via llama-3.3-70b)
    # before retrieval and EPK. Latin-script languages pass through unchanged.
    # Position: after text extraction, before retrieval — per architecture.md §4.
    try:
        from llm.multilingual_preprocessor import PreprocessorInput, preprocess as ml_preprocess
        ml_result = await ml_preprocess(PreprocessorInput(text=text, lang=lang))
        if ml_result.was_normalized:
            logger.info("Multilingual normalization applied", extra={
                "model": ml_result.model_used,
                "lang":  lang,
            })
            text = ml_result.text
    except Exception as exc:
        logger.warning("Multilingual preprocessor failed (non-critical)", extra={"error": str(exc)})

    # ── Safety Gate Pass 2 — deep classification (AFTER Feature Extraction) ───
    try:
        from security.safety_gate import check_pass2, GateVerdict as GV2
        gate2 = await asyncio.wait_for(check_pass2(text), timeout=12.0)
        if gate2.verdict == GV2.DENY:
            logger.warning("Safety Gate Pass 2 blocked message", extra={"user_id": user_id})
            from cognition.response_synthesizer import get_system_message
            return OrchestratorResult(
                text=get_system_message("safety_block", lang),
                tier=Tier.FAST, model=gate2.model_used,
                epk_decision=EPKDecision.DENY,
                usage=UsageRecord(
                    input_tokens=0, output_tokens=0,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                ),
                denied=True, deny_reason="safety_gate_pass2", lang=lang,
            )
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 2 timeout — skipping", extra={"user_id": user_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 2 crashed — skipping", extra={"error": str(exc)})

    # ── conversation history ──────────────────────────────────────────────────
    conversation_history: list[dict] | None = None
    history_store = None

    if supabase is not None:
        try:
            from memory.conversation_history import ConversationHistory
            history_store = ConversationHistory(supabase)
            conversation_history = await history_store.get_history(user_id)
            logger.info("History loaded", extra={
                "user_id": user_id,
                "turns":   len(conversation_history),
            })
        except Exception as exc:
            logger.error("History load failed", extra={"error": str(exc)})
            conversation_history = None

    # ── token estimation ──────────────────────────────────────────────────────
    message_tokens = _estimate_tokens(text)
    history_tokens = _estimate_history_tokens(conversation_history)
    input_tokens   = message_tokens + history_tokens

    logger.info("Handling message", extra={
        "user_id":        user_id,
        "input_tokens":   input_tokens,
        "message_tokens": message_tokens,
        "history_tokens": history_tokens,
        "complexity":     complexity,
        "lang":           lang,
    })

    # ── retrieval ─────────────────────────────────────────────────────────────
    retrieved_context = ""
    embedding_tokens  = 0
    rerank_tokens     = 0

    if supabase is not None and redis is not None:
        try:
            from contracts.retrieval_contracts import RetrievalQuery
            from memory.supabase_store import SupabaseStore
            from retrieval.cache.embedding_cache import EmbeddingCache
            from retrieval.cache.query_cache import QueryCache
            from retrieval.cache.rerank_cache import RerankCache
            from retrieval.retrieval_engine import RetrievalEngine

            engine = RetrievalEngine(
                supabase_store=SupabaseStore(supabase),
                query_cache=QueryCache(redis),
                embedding_cache=EmbeddingCache(redis),
                rerank_cache=RerankCache(redis),
            )

            retrieval_result = await engine.retrieve(RetrievalQuery(
                text=text,
                user_id=str(user_id),
                top_k=5,
            ))

            if retrieval_result.documents:
                retrieved_context = "\n\n".join(
                    d.content for d in retrieval_result.documents if d.content
                )
                embedding_tokens = _estimate_tokens(text)
                if retrieval_result.reranked:
                    rerank_tokens = len(retrieval_result.documents) * 10

            logger.info("Retrieval done", extra={
                "user_id":  user_id,
                "docs":     len(retrieval_result.documents),
                "reranked": retrieval_result.reranked,
                "cached":   retrieval_result.cached,
                "chars":    len(retrieved_context),
            })

        except Exception as exc:
            logger.warning("Retrieval failed, continuing without context", extra={
                "error": str(exc),
            })

    # ── web search fallback ───────────────────────────────────────────────────
    _forced_intent: object = locals().get("_vision_intent_result")

    if not retrieved_context:
        try:
            from cognition.intent_engine import classify
            from external.web_tools import run_tool

            _pre_intent  = locals().get("_vision_intent_result")
            quick_intent = (
                _pre_intent if _pre_intent is not None
                else await classify(text, lang=lang, supabase=supabase, hf_client=hf_client)
            )
            intent_value = quick_intent.intent.value

            _ORCHESTRATOR_TOOLS = {"weather", "maps", "maps_poi", "maps_route", "search"}
            if intent_value not in _NO_SEARCH_INTENTS and intent_value not in _ORCHESTRATOR_TOOLS:
                web_result = await run_tool(
                    tool_name="search",
                    params={"query": text, "lang": lang},
                    lang=lang,
                )
                if web_result:
                    retrieved_context = web_result
                    logger.info("Web search used", extra={
                        "user_id": user_id,
                        "intent":  intent_value,
                        "chars":   len(web_result),
                    })

            _forced_intent = quick_intent

        except Exception as exc:
            logger.warning("Web search failed", extra={"error": str(exc)})

    # ── run pipeline ──────────────────────────────────────────────────────────

    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        input_tokens=input_tokens,
        complexity=complexity,
        lang=lang,
        supabase=supabase,
        hf_client=hf_client,
        conversation_history=conversation_history,
        retrieved_context=retrieved_context,
        embedding_tokens=embedding_tokens,
        rerank_tokens=rerank_tokens,
        forced_intent=_forced_intent,
    )

    result = await run(request)

    # ── save history ──────────────────────────────────────────────────────────
    if history_store is not None and not result.denied:
        try:
            await history_store.append(user_id, "user", text)
            if result.text:
                await history_store.append(user_id, "assistant", result.text)
        except Exception as exc:
            logger.error("History save failed", extra={"error": str(exc)})

    # ── meta layer: reflection + memory_audit (async side-channel) ────────────
    try:
        from meta.reflection import ReflectionInput, reflect
        from meta.memory_audit import MemorySnapshot, audit

        ref_input = ReflectionInput(
            intent=str(result.epk_decision),
            lang=lang,
            tier=str(result.tier),
            model=result.model or "",
            response_text=result.text or "",
            response_truncated=len(result.text or "") >= 4096,
            cost_usd=result.usage.cost_usd,
            was_degraded_mode=str(result.epk_decision) == "DEGRADED_MODE",
            safety_blocked=result.deny_reason == "safety_block",
            user_id=user_id,
        )
        report = reflect(ref_input)
        logger.info("Reflection", extra=report.to_dict())

        snap = MemorySnapshot(
            user_id=user_id,
            history_turn_count=len(conversation_history) if conversation_history else 0,
            snapshot_available=True,
        )
        audit_report = audit(snap)
        if not audit_report.is_healthy():
            logger.warning("Memory audit", extra=audit_report.to_dict())

    except Exception as exc:
        logger.warning("Meta layer failed (non-critical)", extra={"error": str(exc)})

    # ── TTS (voice response when input was voice) ─────────────────────────────
    if _is_voice_input and result.text and not result.denied:
        try:
            from external.text_to_speech import synthesize as tts_synthesize
            tts_result = await tts_synthesize(text=result.text, lang=lang)
            if tts_result.success:
                from dataclasses import replace
                result = replace(result, tts_audio_bytes=tts_result.audio_bytes)
                logger.info(
                    "TTS synthesis complete",
                    extra={"chars": tts_result.char_count, "model": tts_result.model_used},
                )
        except Exception as exc:
            logger.warning("TTS failed — returning text-only", extra={"error": str(exc)})

    return result