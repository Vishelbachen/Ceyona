import logging

from contracts.retrieval_contracts import RetrievalQuery, RetrievalResult, RetrievalDocument
from retrieval.query_preprocessor import preprocess

logger = logging.getLogger(__name__)


async def retrieve(query: RetrievalQuery) -> RetrievalResult:
    """
    ONLY entry point for retrieval system.
    Orchestrates: cache → embed → sparse → hybrid → rerank → return.
    Returns ranked document set. No interpretation. No inference.
    """
    processed = preprocess(query.text)

    # ── embedding ────────────────────────────────────────
    embedding_tokens = 0
    rerank_tokens = 0
    cache_hit = False

    try:
        from retrieval.cache.query_cache import query_cache
        cached = await query_cache.get(processed)
        if cached is not None:
            logger.info("Retrieval cache hit")
            return RetrievalResult(
                query=query.text,
                documents=cached,
                cache_hit=True,
            )
    except Exception as exc:
        logger.warning("Cache check failed", extra={"error": str(exc)})

    # ── dense retrieval ──────────────────────────────────
    dense_docs: list[RetrievalDocument] = []
    try:
        from retrieval.dense.bge_engine import retrieve_dense
        dense_docs, embedding_tokens = await retrieve_dense(
            query=processed,
            user_id=query.user_id,
            top_k=query.top_k * 2,
            embedding_type=query.embedding_type,
        )
    except Exception as exc:
        logger.warning("Dense retrieval failed", extra={"error": str(exc)})

    # ── sparse retrieval ─────────────────────────────────
    sparse_docs: list[RetrievalDocument] = []
    try:
        from retrieval.sparse.bm25_engine import retrieve_sparse
        sparse_docs = await retrieve_sparse(processed, top_k=query.top_k * 2)
    except Exception as exc:
        logger.warning("Sparse retrieval failed", extra={"error": str(exc)})

    # ── hybrid fusion ────────────────────────────────────
    fused: list[RetrievalDocument] = []
    try:
        from retrieval.fusion.hybrid_scorer import fuse
        fused = fuse(dense_docs, sparse_docs, top_k=query.top_k * 2)
    except Exception as exc:
        logger.warning("Fusion failed, using dense", extra={"error": str(exc)})
        fused = dense_docs

    # ── reranker ─────────────────────────────────────────
    final: list[RetrievalDocument] = fused
    if query.use_reranker and fused:
        try:
            from retrieval.reranker.cross_encoder import rerank
            final, rerank_tokens = await rerank(processed, fused, top_k=query.top_k)
        except Exception as exc:
            logger.warning("Reranker failed, using fused", extra={"error": str(exc)})
            final = fused[:query.top_k]
    else:
        final = fused[:query.top_k]

    result = RetrievalResult(
        query=query.text,
        documents=final,
        embedding_tokens=embedding_tokens,
        rerank_tokens=rerank_tokens,
        cache_hit=False,
    )

    # ── write cache ──────────────────────────────────────
    try:
        from retrieval.cache.query_cache import query_cache
        await query_cache.set(processed, final)
    except Exception as exc:
        logger.warning("Cache write failed", extra={"error": str(exc)})

    return result