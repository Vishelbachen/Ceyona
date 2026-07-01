from __future__ import annotations

import logging

from contracts.retrieval_contracts import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedDocument,
)
from retrieval.dense.bge_engine import bge_engine
from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
from retrieval.query_preprocessor import extract_query_profile, preprocess
from retrieval.reranker.cross_encoder import cross_encoder
from retrieval.retrieval_models import RetrievalMetadata, ScoredCandidate
from retrieval.source_credibility import source_credibility
from retrieval.sparse.bm25_engine import BM25Engine

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

    # ── hybrid retrieval: pgvector (dense) + BM25 (sparse) ──────────────────
    # Two independent searches run against the user's full memory corpus.
    # Results are fused via Reciprocal Rank Fusion, then passed to the reranker.
    # BM25 corpus limit is intentionally higher than pgvector top_k so sparse
    # retrieval has enough documents to find lexically relevant matches that
    # dense search may miss (exact names, codes, rare terms).
    _BM25_CORPUS_LIMIT = 200

    candidates: list[tuple[str, float]] = []
    dense_candidates: list[tuple[str, float]] = []
    sparse_candidates: list[tuple[str, float]] = []

    effective_user_id = user_id or getattr(query, "user_id", None)

    if supabase is not None and effective_user_id is not None and dense_result.embedding:
        from memory.supabase_store import SupabaseStore
        store = SupabaseStore(supabase)

        # ── dense: pgvector similarity search ────────────────────────────────
        try:
            records = await store.similarity_search(
                embedding=dense_result.embedding,
                user_id=str(effective_user_id),
                limit=query.top_k,
                threshold=0.7,
            )
            scored_records = source_credibility.score_memory_records(records)
            dense_candidates = [
                ScoredCandidate(
                    content=r.content,
                    score=r.similarity,
                    source="memory",
                    metadata={
                        "document_id": str(r.id),
                        "mem_type": r.mem_type,
                        "source_url": r.source_url or "",
                    },
                    retrieval=RetrievalMetadata(dense_score=round(r.similarity, 4)),
                )
                for r in scored_records
            ]
            logger.info(
                "pgvector similarity search completed",
                extra={"user_id": str(effective_user_id), "candidates": len(dense_candidates)},
            )
        except Exception as exc:
            logger.error(
                "pgvector similarity search failed — continuing without dense candidates",
                extra={"error": str(exc)},
            )

        # ── sparse: BM25 over full user memory corpus ─────────────────────────
        try:
            all_records = await store.fetch_by_user(
                user_id=str(effective_user_id),
                limit=_BM25_CORPUS_LIMIT,
            )
            if all_records:
                bm25 = BM25Engine()
                corpus = [r.content for r in all_records]
                bm25.index(corpus)
                bm25_results = bm25.search(clean_query, top_k=query.top_k)
                sparse_candidates = [
                    ScoredCandidate(
                        content=r.content,
                        score=r.score,
                        source="bm25",
                        retrieval=RetrievalMetadata(sparse_score=round(r.score, 4)),
                    )
                    for r in bm25_results
                ]
                logger.info(
                    "BM25 sparse search completed",
                    extra={"corpus_size": len(corpus), "hits": len(sparse_candidates)},
                )
        except Exception as exc:
            logger.error(
                "BM25 sparse search failed — continuing without sparse candidates",
                extra={"error": str(exc)},
            )

        # ── fusion: RRF combines dense + sparse ───────────────────────────────
        if dense_candidates or sparse_candidates:
            # hybrid_scorer expects list[tuple[str,float]] | list[FusedResult].
            # Pass ScoredCandidates as tuples; provenance is in RetrievalMetadata.
            fused = reciprocal_rank_fusion(
                sparse_results=[(c.content, c.score) for c in sparse_candidates],
                dense_results=[(c.content, c.score) for c in dense_candidates],
                query=clean_query,
                lang=profile.lang,
            )
            # Preserve provenance: merge per-source scores into RetrievalMetadata.
            _prior: dict[str, ScoredCandidate] = {
                c.content: c
                for c in (*dense_candidates, *sparse_candidates)
            }
            candidates = [
                ScoredCandidate(
                    content=r.content,
                    score=r.score,
                    source=r.source,  # "hybrid"
                    metadata=_prior[r.content].metadata if r.content in _prior else {},
                    retrieval=RetrievalMetadata(
                        dense_score=_prior[r.content].retrieval.dense_score if r.content in _prior else None,
                        sparse_score=_prior[r.content].retrieval.sparse_score if r.content in _prior else None,
                        rrf_score=round(r.metadata.get("rrf_score", r.score), 6),
                        geo_score=round(r.metadata.get("geo_score", 0.0), 3),
                        dense_rank=r.metadata.get("dense_rank"),
                        sparse_rank=r.metadata.get("sparse_rank"),
                    ),
                )
                for r in fused
            ]
            logger.info(
                "RRF fusion completed",
                extra={
                    "dense": len(dense_candidates),
                    "sparse": len(sparse_candidates),
                    "fused": len(candidates),
                },
            )
        else:
            candidates = []

    else:
        logger.debug(
            "hybrid retrieval skipped",
            extra={
                "has_supabase": supabase is not None,
                "has_user_id": effective_user_id is not None,
                "has_embedding": bool(dense_result.embedding),
            },
        )

    # ── credibility weighting ────────────────────────────────────────────────
    # credibility is a pass-through for tuple lists; ScoredCandidates already
    # carry provenance via source_credibility.score_memory_records() above.
    pre_credibility_count = len(candidates)
    logger.debug(
        "source_credibility pass-through (ScoredCandidate path)",
        extra={"candidates": pre_credibility_count},
    )

    # ── rerank if candidates available ────────────────────────────────────────
    # Build a content→candidate index to restore provenance after reranking.
    _cand_index: dict[str, ScoredCandidate] = {c.content: c for c in candidates}

    if candidates:
        reranked = await cross_encoder.rerank(
            clean_query, [c.content for c in candidates]  # ScoredCandidate
        )
        top = reranked[: query.rerank_top_k]

        _query_tokens = max(1, len(clean_query) // 4)
        _candidate_texts = [c.content for c in candidates]  # ScoredCandidate
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

    # Convert ScoredCandidates → RetrievedDocument for the external contract.
    # context_mapper.to_context_chunks() handles the retrieval→context conversion
    # when the context layer needs ContextChunks, use context_mapper.to_context_chunks().
    # Here we go directly to RetrievedDocument for the orchestrator contract.
    documents = [
        RetrievedDocument(
            content=content,
            score=score,
            source=_cand_index[content].source if content in _cand_index else "hybrid",
            source_url=_cand_index[content].metadata.get("source_url", "") if content in _cand_index else "",
            metadata={
                "doc": _cand_index[content].metadata if content in _cand_index else {},
                "retrieval": {
                    "dense_score": _cand_index[content].retrieval.dense_score if content in _cand_index else None,
                    "sparse_score": _cand_index[content].retrieval.sparse_score if content in _cand_index else None,
                    "rrf_score": _cand_index[content].retrieval.rrf_score if content in _cand_index else None,
                    "geo_score": _cand_index[content].retrieval.geo_score if content in _cand_index else None,
                    "dense_rank": _cand_index[content].retrieval.dense_rank if content in _cand_index else None,
                    "sparse_rank": _cand_index[content].retrieval.sparse_rank if content in _cand_index else None,
                    "rerank_score": round(score, 4),
                    "query_kind": profile.query_kind,
                    "query_location": profile.location,
                    "query_lang": profile.lang,
                },
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