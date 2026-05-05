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
        return await retrieve(query)


# ─── FUNCTION-BASED API (internal) ────────────────────────────────────────────

async def retrieve(
    query: RetrievalQuery,
    redis=None,
) -> RetrievalResult:
    """
    ONLY entry point for all retrieval operations.
    Returns ranked document set. No interpretation.
    """
    clean_query     = preprocess(query.text)
    embedding_tokens = 0
    rerank_tokens   = 0
    cache_hit       = False

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

    # ── memory similarity search ───────────────────────────────────────────────
    candidates: list[str] = []

    # ── rerank if candidates available ────────────────────────────────────────
    if candidates:
        reranked     = await cross_encoder.rerank(clean_query, candidates)
        rerank_tokens = max(1, len(candidates) * len(clean_query) // 100)
        top          = reranked[: query.rerank_top_k]
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