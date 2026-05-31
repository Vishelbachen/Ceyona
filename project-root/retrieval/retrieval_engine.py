from __future__ import annotations

import logging

from contracts.retrieval_contracts import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedDocument,
)
from retrieval.dense.bge_engine import bge_engine
from retrieval.query_preprocessor import extract_query_profile, preprocess
from retrieval.reranker.cross_encoder import cross_encoder
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
        self._supabase_store = supabase_store
        self._query_cache = query_cache
        self._embedding_cache = embedding_cache
        self._rerank_cache = rerank_cache

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
    profile = extract_query_profile(query.text)
    clean_query = preprocess(query.text)
    embedding_tokens = 0
    rerank_tokens = 0
    cache_hit = False

    logger.debug(
        "Retrieval query profile",
        extra={
            "kind": profile.query_kind,
            "is_geo": profile.is_geo_query,
            "location": profile.location,
            "lang": profile.lang,
        },
    )

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
            candidates = [(r.content, r.similarity) for r in records]
            logger.info(
                "pgvector similarity search completed",
                extra={
                    "user_id": str(effective_user_id),
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
                "has_supabase": supabase is not None,
                "has_user_id": effective_user_id is not None,
                "has_embedding": bool(dense_result.embedding),
            },
        )

    # ── credibility weighting for memory documents ───────────────────────────
    pre_credibility_count = len(candidates)
    candidates = source_credibility.score_documents(candidates)
    if len(candidates) != pre_credibility_count:
        logger.info(
            "source_credibility filtered memory candidates",
            extra={"before": pre_credibility_count, "after": len(candidates)},
        )
    else:
        logger.debug(
            "source_credibility pass-through (no source_url on MemoryRecord yet)",
            extra={"candidates": len(candidates)},
        )

    # ── rerank if candidates available ────────────────────────────────────────
    if candidates:
        reranked = await cross_encoder.rerank(clean_query, [content for content, _ in candidates])
        top = reranked[: query.rerank_top_k]

        _query_tokens = max(1, len(clean_query) // 4)
        _candidate_texts = [c if isinstance(c, str) else c[0] for c in candidates]
        _avg_doc_tokens = max(1, sum(len(t) for t in _candidate_texts) // (4 * len(_candidate_texts)))
        rerank_tokens = (_query_tokens + _avg_doc_tokens) * len(candidates)
        logger.debug(
            "Rerank token estimation",
            extra={
                "query_tokens": _query_tokens,
                "avg_doc_tokens": _avg_doc_tokens,
                "num_candidates": len(candidates),
                "rerank_tokens": rerank_tokens,
                "query_kind": profile.query_kind,
                "location": profile.location,
            },
        )
    else:
        top = []

    documents = [
        RetrievedDocument(
            content=content,
            score=score,
            metadata={
                "query_kind": profile.query_kind,
                "query_location": profile.location,
                "query_lang": profile.lang,
            },
        )
        for content, score in top
    ]

    logger.info("Retrieval complete", extra={
        "query_len": len(clean_query),
        "docs_returned": len(documents),
        "embedding_tokens": embedding_tokens,
        "rerank_tokens": rerank_tokens,
    })

    return RetrievalResult(
        documents=documents,
        embedding_tokens=embedding_tokens,
        rerank_tokens=rerank_tokens,
        cache_hit=cache_hit,
    )