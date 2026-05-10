from __future__ import annotations

import logging
import traceback

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, UsageRecord, run
from transport.telegram.message_router import UpdateType, extract_text, extract_photo, has_photo

logger = logging.getLogger(__name__)

# Model label used when vision fast-path returns a direct response.
# Matches the extraction model defined in vision_handler.py.
_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Intents that generate freely — no web search needed
_NO_SEARCH_INTENTS = {"creative", "conversation", "code", "math"}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_history_tokens(history: list[dict] | None) -> int:
    if not history:
        return 0
    return sum(_estimate_tokens(t.get("content", "")) for t in history)


def _classify_complexity(text: str) -> Complexity:
    has_code = "```" in text or "    " in text
    has_json = "{" in text and "}" in text
    length = len(text)

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

        try:
            from transport.telegram.vision_handler import handle_vision
            vision_result = await handle_vision(
                file_id=file_id,
                caption=caption,
                lang=lang,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(f"Vision handler crashed: {exc!r}\n{tb}")
            from cognition.response_synthesizer import get_system_message
            error_text = get_system_message("vision_error", lang)
            return OrchestratorResult(
                text=error_text,
                tier=Tier.FAST,
                model="",
                epk_decision=EPKDecision.DENY,
                usage=UsageRecord(
                    input_tokens=0,
                    output_tokens=0,
                    embedding_tokens=0,
                    rerank_tokens=0,
                    tier=Tier.FAST,
                    embedding_type="large",
                    cost_usd=0.0,
                ),
                denied=True,
                deny_reason="vision_error",
                lang=lang,
            )

        # ── CASE 1: descriptive / conversational — direct response ────────────
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
                    embedding_tokens=0,
                    rerank_tokens=0,
                    tier=Tier.GENERAL,
                    embedding_type="large",
                    cost_usd=0.001,
                ),
                denied=False,
                deny_reason="",
                lang=lang,
            )

        # ── CASE 2: analytical / task — forward extracted text into pipeline ──
        logger.info("Vision pipeline-path: forwarding to orchestrator", extra={"user_id": user_id})
        # Fall through to the standard text pipeline below,
        # using the extracted vision text as the user message.
        update = dict(update)           # shallow copy — do not mutate the original
        _vision_text_override   = vision_result.text
        _vision_intent_result   = vision_result.intent_result  # may be None if classify failed

    # ── text handling (original flow) ─────────────────────────────────────────
    # If vision pipeline-path set an override, use extracted image text;
    # otherwise extract text from the Telegram update as normal.
    text = locals().get("_vision_text_override") or extract_text(update)

    if not text:
        logger.info("Empty text update ignored", extra={"user_id": user_id})
        return OrchestratorResult(
            text="",
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                rerank_tokens=0,
                tier=Tier.FAST,
                embedding_type="large",
                cost_usd=0.0,
            ),
            denied=True,
            deny_reason="empty_message",
            lang=lang,
        )

    complexity = _classify_complexity(text)

    # ── load conversation history ─────────────────────────────────────────────
    conversation_history: list[dict] | None = None
    history_store = None

    if supabase is not None:
        try:
            from memory.conversation_history import ConversationHistory
            history_store = ConversationHistory(supabase)
            conversation_history = await history_store.get_history(user_id)
            logger.info("History loaded", extra={
                "user_id": user_id,
                "turns": len(conversation_history),
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

    # ── retrieval (vector search in Supabase memory) ──────────────────────────
    retrieved_context = ""
    embedding_tokens  = 0
    rerank_tokens     = 0

    if supabase is not None and redis is not None:
        try:
            from retrieval.retrieval_engine import RetrievalEngine
            from retrieval.cache.embedding_cache import EmbeddingCache
            from retrieval.cache.query_cache import QueryCache
            from retrieval.cache.rerank_cache import RerankCache
            from memory.supabase_store import SupabaseStore
            from contracts.retrieval_contracts import RetrievalQuery

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
                threshold=0.65,
                use_reranker=True,
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

    # ── web search ────────────────────────────────────────────────────────────
    # For vision pipeline-path, intent is already known — reuse it directly
    # to avoid a redundant classify() call before the orchestrator does its own.
    if not retrieved_context:
        try:
            from cognition.intent_engine import classify
            from external.web_tools import run_tool

            _pre_intent    = locals().get("_vision_intent_result")
            quick_intent   = _pre_intent if _pre_intent is not None else classify(text, lang=lang)
            intent_value   = quick_intent.intent.value

            if intent_value not in _NO_SEARCH_INTENTS:
                if intent_value in ("weather", "maps", "maps_poi"):
                    web_result = await run_tool(
                        tool_name=intent_value,
                        params={"query": text, "lang": lang},
                        lang=lang,
                    )
                else:
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

        except Exception as exc:
            logger.warning("Web search failed", extra={"error": str(exc)})

    # Pass pre-computed intent from vision pipeline when available.
    # Orchestrator will skip classify() and use it directly.
    _forced_intent = locals().get("_vision_intent_result")

    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        input_tokens=input_tokens,
        complexity=complexity,
        lang=lang,
        conversation_history=conversation_history,
        retrieved_context=retrieved_context,
        embedding_tokens=embedding_tokens,
        rerank_tokens=rerank_tokens,
        forced_intent=_forced_intent,
    )

    result = await run(request)

    # ── save turns to history ─────────────────────────────────────────────────
    if history_store is not None and not result.denied:
        try:
            await history_store.append(user_id, "user", text)
            if result.text:
                await history_store.append(user_id, "assistant", result.text)
        except Exception as exc:
            logger.error("History save failed", extra={"error": str(exc)})

    return result