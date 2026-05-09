from __future__ import annotations

import logging

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, UsageRecord, run
from transport.telegram.message_router import UpdateType, extract_text, extract_photo, has_photo

logger = logging.getLogger(__name__)

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
        file_id = photo_meta["file_id"]
        caption = photo_meta.get("caption", "")

        logger.info("Photo message received", extra={
            "user_id": user_id,
            "file_id": file_id[:20],
            "caption": caption[:50],
        })

        try:
            from transport.telegram.vision_handler import handle_vision
            vision_text = await handle_vision(
                file_id=file_id,
                caption=caption,
                lang=lang,
            )
        except Exception as exc:
            logger.error("Vision handler crashed", extra={"error": str(exc)})
            vision_text = "❌ Image processing error."

        # Return as OrchestratorResult so webhook pipeline stays uniform
        return OrchestratorResult(
            text=vision_text,
            tier=Tier.GENERAL,
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            epk_decision=EPKDecision.ALLOW,
            usage=UsageRecord(
                input_tokens=_estimate_tokens(caption) + 500,  # rough image token estimate
                output_tokens=_estimate_tokens(vision_text),
                embedding_tokens=0,
                rerank_tokens=0,
                tier=Tier.GENERAL,
                embedding_type="large",
                cost_usd=0.001,  # minimal cost placeholder
            ),
            denied=False,
            deny_reason="",
            lang=lang,
        )

    # ── text handling (original flow) ─────────────────────────────────────────
    text = extract_text(update)

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

    # ── web search (always runs for non-generative intents) ───────────────────
    # Runs for QUESTION, ANALYSIS, INSTRUCTION, SEARCH, UNKNOWN — always fetches
    # live data so the bot NEVER says "my data may be outdated".
    # Skipped for CREATIVE, CONVERSATION, CODE, MATH — no grounding needed.
    if not retrieved_context:
        try:
            from cognition.intent_engine import classify
            from external.web_tools import run_tool

            quick_intent = classify(text, lang=lang)
            intent_value = quick_intent.intent.value

            if intent_value not in _NO_SEARCH_INTENTS:
                if intent_value in ("weather", "maps", "maps_poi"):
                    web_result = await run_tool(
                        tool_name=intent_value,
                        params={"query": text, "lang": lang},
                        lang=lang,
                    )
                else:
                    # Always do a web search — guarantees current information
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