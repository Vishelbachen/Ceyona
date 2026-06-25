from __future__ import annotations

import asyncio
import logging
import traceback

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import (
    OrchestratorRequest,
    OrchestratorResult,
    UsageRecord,
    run,
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

_VISION_MODEL      = "qwen/qwen3.6-27b"

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_history_tokens(history: list[dict] | None) -> int:
    if not history:
        return 0
    return sum(_estimate_tokens(t.get("content", "")) for t in history)


def _classify_complexity(text: str) -> Complexity:
    """
    Classify message complexity for EPK cost estimation.

    Previous heuristic was noisy: 4 spaces anywhere = HIGH,
    any "{}" = HIGH. This caused false DEGRADED_MODE for casual messages.

    Fixed (audit §1.2):
    - Code block detection: only fenced blocks (```), not indentation
    - JSON detection: requires both braces AND colon (key:value pattern)
    - Length threshold raised: 800 chars (previously 500 gave too many MEDIUM)
    - Results are logged so the signal is observable
    """
    stripped = text.strip()
    length   = len(stripped)

    has_code = "```" in stripped
    has_json = "{" in stripped and "}" in stripped and ":" in stripped

    if has_code and has_json:
        complexity = Complexity.CRITICAL
    elif has_code or has_json:
        complexity = Complexity.HIGH
    elif length > 800:
        complexity = Complexity.MEDIUM
    else:
        complexity = Complexity.LOW

    logger.debug(
        "Complexity classified",
        extra={"complexity": complexity, "length": length, "has_code": has_code, "has_json": has_json},
    )
    return complexity


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
    vision_intent=None,  # IntentResult | None — pre-classified by vision handler, skips re-classify
    is_vision: bool = False,  # routing guard: True when user_message is extracted image content
                               # (not raw user text). Prevents CoT reasoning on vision pipeline path.
                               # Set explicitly by callers on album path; auto-detected on single photo path.
) -> OrchestratorResult:

    # ── photo handling ────────────────────────────────────────────────────────
    if has_photo(update):
        photo_meta   = extract_photo(update)
        file_id      = photo_meta["file_id"]
        caption      = photo_meta.get("caption", "")
        group_id     = extract_media_group_id(update)
        message_id   = extract_message_id(update)

        logger.info("Photo message received", extra={
            "user_id":  user_id,
            "file_id":  file_id[:20],
            "caption":  caption[:50],
            "group_id": group_id,
        })

        # ── album photo: buffer in aggregator, respond when group is ready ────
        if group_id and redis is not None:
            from transport.telegram.media_group_aggregator import (
                MediaGroupAggregator,
                MediaGroupItem,
            )

            # Prefix group_id with chat_id so the callback can resolve the recipient.
            scoped_group_id = f"{user_id}:{group_id}"

            # Retrieve the app-level aggregator from app state if available.
            aggregator: MediaGroupAggregator | None = getattr(
                app_state, "media_group_aggregator", None
            )

            if aggregator is None:
                # Fallback: app_state not wired (shouldn't happen in prod).
                # Must call start() to register Lua scripts — skipping it
                # leaves _lua_add=None and crashes on aggregator.add().
                logger.warning(
                    "MediaGroupAggregator not in app_state — creating ephemeral fallback",
                    extra={"user_id": user_id},
                )
                async def _noop_callback(gid: str, items) -> None:  # noqa: E731
                    pass
                aggregator = MediaGroupAggregator(redis, _noop_callback)
                await aggregator.start()

            item = MediaGroupItem(
                file_id=file_id,
                message_id=message_id,
                caption=caption,
                lang=lang,
            )
            await aggregator.add(scoped_group_id, item)

            # Return early — the aggregator callback will send the reply once
            # all photos in the album have arrived.
            from i18n.t import get_system_message
            return OrchestratorResult(
                text="",   # empty → webhook suppresses send
                tier=Tier.FAST,
                model="",
                epk_decision=EPKDecision.ALLOW,
                usage=UsageRecord(
                    input_tokens=0, output_tokens=0,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                ),
                denied=False,
                deny_reason="",
                lang=lang,
            )

        # Safety Gate Pass 1 on caption (photo text)
        # NON-BLOCKING per architecture.md §21 — check_pass1 always returns PASS.
        # DENY branch removed: safety_gate v2 (May 2026) is observability-only.
        # Blocking authority: safety_agent (post-reasoning).
        if caption:
            try:
                from security.safety_gate import check_pass1
                await asyncio.wait_for(check_pass1(caption), timeout=8.0)
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
            from i18n.t import get_system_message
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
            # Fix §9.3: vision fast-path previously bypassed EPK entirely.
            # cost_usd was hardcoded to 0.001 and balance was never checked —
            # zero-balance users received free vision responses.
            # Now: run a balance guard before returning. We can't run a full EPK
            # estimate here (no embedding_tokens, no complexity), so we use the
            # §D billing fix: compute actual cost from Groq token counts before guard.
            # vision_cost() uses _VISION_RATES ($0.60/$3.00 per 1M) from payments/pricing_engine.
            # Model: qwen/qwen3.6-27b (replaces llama-4-scout, deprecated Jul 17, 2026).
            # Falls back to conservative $0.001 estimate if tokens weren't captured (failed=True path).
            from payments.pricing_engine import vision_cost
            _vision_cost_usd = vision_cost(
                input_tokens=vision_result.vision_input_tokens,
                output_tokens=vision_result.vision_output_tokens,
            ) or 0.001
            if user_balance <= 0 or _vision_cost_usd > user_balance:
                logger.warning(
                    "Vision fast-path: balance insufficient — denying",
                    extra={"user_id": user_id, "balance": user_balance, "cost": _vision_cost_usd},
                )
                from i18n.t import get_system_message
                return OrchestratorResult(
                    text=get_system_message("insufficient_balance", lang),
                    tier=Tier.FAST,
                    model="",
                    epk_decision=EPKDecision.DENY,
                    usage=UsageRecord(
                        input_tokens=0, output_tokens=0,
                        embedding_tokens=0, rerank_tokens=0,
                        tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                    ),
                    denied=True,
                    deny_reason="insufficient_balance",
                    lang=lang,
                )
            logger.info("Vision fast-path: direct response", extra={"user_id": user_id})
            final_text = vision_result.text
            return OrchestratorResult(
                text=final_text,
                tier=Tier.GENERAL,
                model=_VISION_MODEL,
                epk_decision=EPKDecision.ALLOW,
                usage=UsageRecord(
                    input_tokens=vision_result.vision_input_tokens,
                    output_tokens=vision_result.vision_output_tokens,
                    embedding_tokens=0, rerank_tokens=0,
                    tier=Tier.GENERAL, embedding_type="large", cost_usd=_vision_cost_usd,
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
        # For history: save what the user actually sent (caption), not the vision dump.
        # Vision dump can be thousands of tokens — saving it causes 413 on next requests.
        _vision_caption_for_history = caption if caption.strip() else "[фото]"

    # ── voice/audio handling (ASR → transcript → pipeline) ───────────────────
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
                from security.safety_gate import check_pass1

                audio_bytes, filename = await download_telegram_voice(
                    file_id=voice_file_id,
                    bot_token=settings.bot_token,
                )

                # ── VAD: skip Whisper on fully silent audio ───────────────────
                # ffmpeg silencedetect: if recording never rose above noise floor
                # → user pressed PTT without speaking.
                # Return a soft "didn't catch that" instead of a generic error.
                _voice_ext = filename.rsplit(".", 1)[-1].lower()
                if await is_silent(audio_bytes, source_ext=_voice_ext):
                    logger.info(
                        "VAD: silent audio — returning vad_silence",
                        extra={"user_id": user_id, "bytes": len(audio_bytes)},
                    )
                    from i18n.t import get_system_message
                    return OrchestratorResult(
                        text=get_system_message("vad_silence", lang),
                        tier=Tier.FAST, model="",
                        epk_decision=EPKDecision.DENY,
                        usage=UsageRecord(
                            input_tokens=0, output_tokens=0,
                            embedding_tokens=0, rerank_tokens=0,
                            tier=Tier.FAST, embedding_type="large", cost_usd=0.0,
                        ),
                        denied=True, deny_reason="vad_silence", lang=lang,
                    )

                tr = await transcribe(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    lang=lang if lang != "en" else None,
                )

                if not tr.success or not tr.text:
                    logger.warning("ASR failed", extra={"user_id": user_id})
                    from i18n.t import get_system_message
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
                        from i18n.t import get_system_message
                        # Safety Gate ran and consumed tokens — carry them so
                        # webhook bills gate cost even on DENY (economic.md §2).
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
                            safety_pass1_tokens=gate1.tokens_used,
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
                logger.error("Voice path crashed", extra={
                    "user_id": user_id,
                    "error": str(exc) or "(empty)",
                    "exc_type": type(exc).__name__,
                })

    # ── text extraction ───────────────────────────────────────────────────────
    # Vision pipeline path with caption: caption is the user's question; image
    # descriptions are supporting context, not the topic. Separating them prevents
    # the main LLM from narrating the photos instead of answering the question.
    _vision_override = locals().get("_vision_text_override")
    _vision_caption  = locals().get("_vision_caption_for_history", "")
    if _vision_override and _vision_caption and _vision_caption != "[фото]":
        text = _vision_caption
        _vision_image_context = _vision_override
    else:
        text = _vision_override or update.get("_voice_transcript") or extract_text(update)
        _vision_image_context = None

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

    # ── Safety Gate Pass 1 — observability only (BEFORE Feature Extraction) ────
    # NON-BLOCKING per architecture.md §21 — check_pass1 always returns PASS.
    # DENY branch removed: safety_gate v2 (May 2026) is observability-only.
    # Blocking authority: safety_agent (post-reasoning).
    _safety_pass1_tokens = 0
    try:
        from security.safety_gate import check_pass1
        _gate1 = await asyncio.wait_for(check_pass1(text), timeout=8.0)
        _safety_pass1_tokens = _gate1.tokens_used
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 1 timeout — skipping", extra={"user_id": user_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 1 crashed — skipping", extra={"error": str(exc)})

    complexity = _classify_complexity(text)

    # ── multilingual normalization ─────────────────────────────────────────────
    # Normalize non-Latin scripts (Arabic via allam-2-7b, others via qwen3.6-27b)
    # before retrieval and EPK. Latin-script languages pass through unchanged.
    # Position: after text extraction, before retrieval — per architecture.md §4.
    _ml_input_tokens  = 0
    _ml_output_tokens = 0
    _ml_model         = "passthrough"
    try:
        from llm.multilingual_preprocessor import PreprocessorInput
        from llm.multilingual_preprocessor import preprocess as ml_preprocess
        ml_result = await ml_preprocess(PreprocessorInput(text=text, lang=lang))
        _ml_input_tokens  = ml_result.input_tokens
        _ml_output_tokens = ml_result.output_tokens
        _ml_model         = ml_result.model_used  # "allam-2-7b" | "qwen/qwen3.6-27b" | "passthrough"
        if ml_result.was_normalized:
            logger.info("Multilingual normalization applied", extra={
                "model": ml_result.model_used,
                "lang":  lang,
            })
            text = ml_result.text
    except Exception as exc:
        logger.warning("Multilingual preprocessor failed (non-critical)", extra={"error": str(exc)})

    # ── Safety Gate Pass 2 — observability only (AFTER Feature Extraction) ─────
    # NON-BLOCKING per architecture.md §21 — check_pass2 always returns PASS.
    # DENY branch removed: safety_gate v2 (May 2026) is observability-only.
    # Blocking authority: safety_agent (post-reasoning).
    _safety_pass2_tokens = 0
    _safety_safeguard_tokens = 0
    _safety_safeguard_output_tokens = 0
    try:
        from security.safety_gate import check_pass2
        _gate2 = await asyncio.wait_for(check_pass2(text), timeout=12.0)
        _safety_pass2_tokens = _gate2.tokens_used                          # 86m input tokens
        _safety_safeguard_tokens = _gate2.safeguard_tokens_used            # safeguard-20b input tokens
        _safety_safeguard_output_tokens = _gate2.safeguard_output_tokens_used  # safeguard-20b output tokens
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 2 timeout — skipping", extra={"user_id": user_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 2 crashed — skipping", extra={"error": str(exc)})

    # ── meta/analysis.py — pre-reasoning structural hints (§4 lifecycle) ────────
    # Pure function, no I/O, never raises. Runs AFTER Pass 2 (normalized text),
    # BEFORE orchestrator. Produces non-binding AnalysisReport for intent_engine.
    # DEGRADED_MODE unknown at this point — lightweight=False (orchestrator will
    # have EPK result; analysis runs pre-EPK with full mode as safe default).
    _analysis_report = None
    try:
        from meta.analysis import analyse as _analyse
        _analysis_report = _analyse(text, lightweight=False)
        logger.debug(
            "analysis.py complete",
            extra={
                "word_count":      _analysis_report.word_count,
                "dominant_script": _analysis_report.dominant_script,
                "hints":           [h.hint.value for h in _analysis_report.hints],
            },
        )
    except Exception as exc:
        # Non-critical — pipeline continues without hints
        logger.warning("analysis.py failed (non-critical)", extra={"error": str(exc)})

    # ── conversation history ──────────────────────────────────────────────────
    # Select token budget before loading history.
    # Tier is unknown here (EPK runs after retrieval), so we use the same
    # heuristic as orchestrator._estimate_tier:
    #   LOW complexity + short message → likely FAST tier → smaller budget
    #   everything else → GENERAL/HEAVY → larger budget
    # This avoids the aggressive 1200-token cap that was cutting history to
    # 0-2 turns and causing bug 13.2 (context loss).
    from memory.conversation_history import (
        FAST_HISTORY_BUDGET,
        GENERAL_HISTORY_BUDGET,
        ConversationHistory,
    )
    _message_tokens_pre = _estimate_tokens(text)
    _history_budget = (
        FAST_HISTORY_BUDGET
        if complexity == Complexity.LOW and _message_tokens_pre < 300
        else GENERAL_HISTORY_BUDGET
    )
    logger.debug("History budget selected", extra={
        "budget":     _history_budget,
        "complexity": complexity,
        "msg_tokens": _message_tokens_pre,
    })

    conversation_history: list[dict] | None = None
    history_store = None

    if supabase is not None and input_type != "image_group":
        # image_group: each album is a self-contained task — loading previous
        # conversation history would cause the model to treat it as a continuation
        # of the last album, mixing batches. History is still WRITTEN after the
        # response so the user's next text message has correct context.
        try:
            history_store = ConversationHistory(supabase)
            conversation_history = await history_store.get_history(
                user_id, token_budget=_history_budget
            )
            logger.info("History loaded", extra={
                "user_id":       user_id,
                "turns":         len(conversation_history),
                "token_budget":  _history_budget,
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
    # Fix §5.4: previously gated on `supabase is not None and redis is not None`.
    # Redis is optional cache — pgvector similarity search only needs Supabase.
    # If Redis is unavailable: retrieval runs without cache (degraded, not skipped).
    # If Supabase is unavailable: retrieval is skipped (pgvector requires it).
    retrieved_context = ""
    embedding_tokens  = 0
    rerank_tokens     = 0

    if supabase is not None:
        if redis is None:
            logger.warning(
                "Retrieval: Redis unavailable — running without cache (degraded)",
                extra={"user_id": user_id},
            )
        try:
            from contracts.retrieval_contracts import RetrievalQuery
            from memory.supabase_store import SupabaseStore
            from retrieval.retrieval_engine import RetrievalEngine

            # Inject cache only when Redis is available.
            # RetrievalEngine handles None values gracefully (no caching).
            engine_kwargs: dict = {"supabase_store": SupabaseStore(supabase)}
            if redis is not None:
                from retrieval.cache.embedding_cache import EmbeddingCache
                from retrieval.cache.query_cache import QueryCache
                from retrieval.cache.rerank_cache import RerankCache
                engine_kwargs["query_cache"]     = QueryCache(redis)
                engine_kwargs["embedding_cache"] = EmbeddingCache(redis)
                engine_kwargs["rerank_cache"]    = RerankCache(redis)

            engine = RetrievalEngine(**engine_kwargs)

            retrieval_result = await engine.retrieve(RetrievalQuery(
                text=text,
                user_id=str(user_id),
                top_k=5,
            ))

            if retrieval_result.documents:
                # Score threshold: only include documents with sufficient relevance.
                # 0.75 is above pgvector similarity_search threshold (0.7) —
                # documents that passed pgvector but scored low on cross-encoder
                # reranking are excluded. This prevents nrerlevant memory records
                # (old conversations, wrong topics) from contaminating context.
                # Authority: update_handler owns context assembly (architecture §4).
                # This is not policy — it is data quality filtering before context build.
                _MIN_RETRIEVAL_SCORE = 0.75
                _relevant_docs = [
                    d for d in retrieval_result.documents
                    if d.content and d.score >= _MIN_RETRIEVAL_SCORE
                ]
                if _relevant_docs:
                    retrieved_context = "\n\n".join(d.content for d in _relevant_docs)
                logger.info("Retrieval score filter applied", extra={
                    "total_docs":    len(retrieval_result.documents),
                    "relevant_docs": len(_relevant_docs),
                    "threshold":     _MIN_RETRIEVAL_SCORE,
                })
                # Use token counts from retrieval_engine (real estimation, fixed §5.2).
                # Do not recompute here — retrieval_engine owns this calculation.
                embedding_tokens = retrieval_result.embedding_tokens
                rerank_tokens    = retrieval_result.rerank_tokens

            logger.info("Retrieval done", extra={
                "user_id":       user_id,
                "docs":          len(retrieval_result.documents),
                "reranked":      retrieval_result.reranked,
                "cached":        retrieval_result.cached,
                "redis_cache":   redis is not None,
                "chars":         len(retrieved_context),
                "emb_tokens":    embedding_tokens,
                "rerank_tokens": rerank_tokens,
            })

        except Exception as exc:
            logger.warning("Retrieval failed, continuing without context", extra={
                "error": str(exc),
            })
    else:
        logger.warning(
            "Retrieval skipped — Supabase unavailable (pgvector requires it)",
            extra={"user_id": user_id},
        )

    # ── run pipeline ──────────────────────────────────────────────────────────

    # Vision caption path: inject image descriptions into retrieved_context.
    # _vision_image_context is set when caption is present (line 346) but was never
    # wired into the pipeline — descriptions were silently dropped. Now they go into
    # retrieved_context so the main LLM treats them as supporting material, not as
    # the topic to narrate. Prevents inference/storytelling from unrelated photo sets.
    _vic = locals().get("_vision_image_context")
    if _vic:
        # VQ-03 guard: anchor model to visible content only.
        # Without this prefix, qwen3.6-27b extrapolates beyond what is visible
        # (e.g. screenshot of Wildberries → "это ChatGPT от OpenAI").
        # The guard instructs the model to answer ONLY from the visual description —
        # never to infer, guess, or name platforms/products not explicitly visible.
        _vic_grounded = (
            "[VISUAL CONTEXT — answer only from what is described below. "
            "Do NOT infer, guess, or name platforms, apps, or entities "
            "unless their name is explicitly visible in the image.]\n"
            + _vic
        )
        retrieved_context = (
            f"[Фото]\n{_vic_grounded}\n\n{retrieved_context}"
            if retrieved_context
            else f"[Фото]\n{_vic_grounded}"
        )

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
        # vision_intent: pre-classified by vision handler (single photo or album).
        # If provided, orchestrator uses it directly — skips re-classify.
        # This prevents double-routing (vision → MAPS/SEARCH) on album path.
        vision_intent=locals().get("_vision_intent_result") or vision_intent,
        skip_web_search=(
            locals().get("_vision_intent_result") is not None
            or vision_intent is not None
        ),
        # is_vision: routing guard against CoT artefacts on vision pipeline path.
        # True when user_message contains extracted image descriptions (not user text).
        # Prevents _classify_complexity() from treating LLM-generated structured text
        # as high-complexity user input → blocks CHAIN_OF_THOUGHT reasoning mode.
        # Set on both single-photo and album paths when needs_pipeline=True.
        is_vision=is_vision or (locals().get("_vision_text_override") is not None),
        request_id=request_id,
        analysis_report=_analysis_report,
        input_type=input_type,
    )

    result = await run(request)

    # ── save history ──────────────────────────────────────────────────────────
    if history_store is not None and not result.denied:
        try:
            # Vision path: save caption (what user actually typed), not the vision extraction dump.
            # Saving the full vision text (potentially 1000+ tokens) into history causes
            # 413 Payload Too Large on subsequent requests — audit §13.2 / vision history fix.
            _user_message_for_history = (
                locals().get("_vision_caption_for_history") or text
            )
            await history_store.append(user_id, "user", _user_message_for_history)
            if result.text:
                await history_store.append(user_id, "assistant", result.text)
        except Exception as exc:
            logger.error("History save failed", extra={"error": str(exc)})

    # ── meta layer: reflection + memory_audit (async side-channel) ────────────
    try:
        from meta.memory_audit import MemorySnapshot, audit
        from meta.reflection import ReflectionInput, reflect

        ref_input = ReflectionInput(
            intent=result.intent or str(result.epk_decision),  # real intent, not EPK decision
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
    _tts_characters = 0
    if _is_voice_input and result.text and not result.denied:
        try:
            from external.text_to_speech import synthesize as tts_synthesize
            tts_result = await tts_synthesize(text=result.text, lang=lang)
            if tts_result.success:
                from dataclasses import replace
                result = replace(result, tts_audio_bytes=tts_result.audio_bytes)
                _tts_characters = tts_result.char_count
                logger.info(
                    "TTS synthesis complete",
                    extra={"chars": tts_result.char_count, "model": tts_result.model_used},
                )
        except Exception as exc:
            logger.warning("TTS failed — returning text-only", extra={"error": str(exc)})

    # ── wire speech billing fields onto result ────────────────────────────────
    # audio_seconds and tts_characters are captured in local vars above.
    # They must be set on OrchestratorResult so webhook.py can pass them
    # to UsageEntry — otherwise speech billing always records 0.
    if (_asr_audio_seconds or _tts_characters
            or _safety_pass1_tokens or _safety_pass2_tokens
            or _safety_safeguard_tokens or _safety_safeguard_output_tokens
            or _ml_input_tokens or _ml_output_tokens):
        from dataclasses import replace as _replace
        result = _replace(result,
            audio_seconds=_asr_audio_seconds,
            tts_characters=_tts_characters,
            safety_pass1_tokens=_safety_pass1_tokens,
            safety_pass2_tokens=_safety_pass2_tokens,
            safety_safeguard_tokens=_safety_safeguard_tokens,
            safety_safeguard_output_tokens=_safety_safeguard_output_tokens,
            multilingual_input_tokens=_ml_input_tokens,
            multilingual_output_tokens=_ml_output_tokens,
            multilingual_model=_ml_model,
        )

    return result