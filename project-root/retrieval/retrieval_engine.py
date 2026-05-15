from __future__ import annotations

import logging
from dataclasses import dataclass, field

from contracts.retrieval_contracts import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedDocument,
)
from retrieval.dense.bge_engine import bge_engine
from retrieval.reranker.cross_encoder import cross_encoder
from retrieval.query_preprocessor import preprocess
from retrieval.source_credibility import source_credibility

logger = logging.getLogger(__name__)


# ─── CLASS-BASED API (used by update_handler) ─────────────────────────────────

class RetrievalEngine:
    """
    Class wrapper around the retrieve() function.
    Accepts injected cache/store dependencies from update_handler.
    """

    def __init__(
        self,
        supabase_store=None,
        query_cache=None,
        embedding_cache=None,
        rerank_cache=None,
    ) -> None:
        self._supabase_store    = supabase_store
        self._query_cache       = query_cache
        self._embedding_cache   = embedding_cache
        self._rerank_cache      = rerank_cache

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        # Pass supabase_store so pgvector similarity search actually fires.
        # Previously retrieve(query) was called without supabase → always empty.
        supabase_client = None
        if self._supabase_store is not None:
            supabase_client = self._supabase_store._db
        return await retrieve(query, supabase=supabase_client, user_id=query.user_id)


# ─── FUNCTION-BASED API (internal) ────────────────────────────────────────────

async def retrieve(
    query: RetrievalQuery,
    redis=None,
    supabase=None,
    user_id: str | None = None,
) -> RetrievalResult:
    """
    ONLY entry point for all retrieval operations.
    Returns ranked document set. No interpretation.

    pgvector similarity search fires when supabase + user_id are provided.
    Falls back gracefully to empty candidates if unavailable.
    """
    clean_query      = preprocess(query.text)
    embedding_tokens = 0
    rerank_tokens    = 0
    cache_hit        = False

    # ── embedding ─────────────────────────────────────────────────────────────
    use_fast = query.embedding_type == "small"
    dense_result = await bge_engine.embed(clean_query, use_fast=use_fast)

    if dense_result is None:
        logger.warning("Embedding failed, returning empty result")
        return RetrievalResult(
            documents=[],
            embedding_tokens=0,
            rerank_tokens=0,
            cache_hit=False,
        )

    embedding_tokens = dense_result.tokens_used

    # ── memory similarity search via pgvector ─────────────────────────────────
    # BUG FIX: previously candidates was always [], pgvector was never called.
    # Now we invoke SupabaseStore.similarity_search() with the fresh embedding.
    candidates: list[tuple[str, float]] = []

    effective_user_id = user_id or getattr(query, "user_id", None)

    if supabase is not None and effective_user_id is not None and dense_result.embedding:
        try:
            from memory.supabase_store import SupabaseStore
            store = SupabaseStore(supabase)
            records = await store.similarity_search(
                embedding=dense_result.embedding,
                user_id=str(effective_user_id),
                limit=query.top_k,
                threshold=0.7,
            )
            candidates = [(r.content, 1.0) for r in records]
            logger.info(
                "pgvector similarity search completed",
                extra={
                    "user_id":    str(effective_user_id),
                    "candidates": len(candidates),
                },
            )
        except Exception as exc:
            logger.error(
                "pgvector similarity search failed — continuing without memory",
                extra={"error": str(exc)},
            )
            candidates = []
    else:
        logger.debug(
            "pgvector skipped",
            extra={
                "has_supabase":  supabase is not None,
                "has_user_id":   effective_user_id is not None,
                "has_embedding": bool(dense_result.embedding),
            },
        )

    # ── credibility weighting for memory documents ───────────────────────────
    # Memory records don't have source URLs yet, so score_documents() is a
    # pass-through. When MemoryRecord gains source_url, weighting activates.
    candidates = source_credibility.score_documents(candidates)

    # ── rerank if candidates available ────────────────────────────────────────
    if candidates:
        reranked      = await cross_encoder.rerank(clean_query, candidates)
        rerank_tokens = max(1, len(candidates) * len(clean_query) // 100)
        top           = reranked[: query.rerank_top_k]
    else:
        top = []

    documents = [
        RetrievedDocument(content=content, score=score)
        for content, score in top
    ]

    logger.info("Retrieval complete", extra={
        "query_len":        len(clean_query),
        "docs_returned":    len(documents),
        "embedding_tokens": embedding_tokens,
        "rerank_tokens":    rerank_tokens,
    })

    return RetrievalResult(
        documents=documents,
        embedding_tokens=embedding_tokens,
        rerank_tokens=rerank_tokens,
        cache_hit=cache_hit,
    )