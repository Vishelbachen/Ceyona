import logging

from contracts.retrieval_contracts import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedDocument,
)
from retrieval.cache.embedding_cache import EmbeddingCache
from retrieval.cache.query_cache import QueryCache
from retrieval.cache.rerank_cache import RerankCache
from retrieval.dense.bge_engine import BGEEngine
from retrieval.fusion.hybrid_scorer import fuse
from retrieval.query_preprocessor import preprocess
from retrieval.reranker.cross_encoder import CrossEncoder
from retrieval.sparse.bm25_engine import BM25Engine
from memory.supabase_store import SupabaseStore

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    ONLY entry point for retrieval.
    Orchestrates: preprocess → cache → dense → sparse → fuse → rerank.
    Returns ranked document sets only. No interpretation.
    """

    def __init__(
        self,
        supabase_store: SupabaseStore,
        query_cache: QueryCache,
        embedding_cache: EmbeddingCache,
        rerank_cache: RerankCache,
    ) -> None:
        self._store = supabase_store
        self._query_cache = query_cache
        self._bge = BGEEngine(embedding_cache)
        self._reranker = CrossEncoder(rerank_cache)

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        clean = preprocess(query.text)

        # ── query cache ──────────────────────────────────
        cached = await self._query_cache.get(clean, query.user_id)
        if cached:
            docs = [RetrievedDocument(**d) for d in cached]
            return RetrievalResult(query=clean, documents=docs, cached=True)

        # ── dense retrieval ──────────────────────────────
        embedding = await self._bge.embed_query(clean)
        dense_records = await self._store.similarity_search(
            embedding=embedding,
            user_id=query.user_id,
            limit=query.top_k * 2,
            threshold=query.threshold,
        )
        dense = [(r.content, 1.0) for r in dense_records]

        # ── sparse retrieval (BM25) ───────────────────────
        corpus = [r.content for r in dense_records]
        bm25 = BM25Engine(corpus)
        sparse_results = bm25.search(clean, top_k=query.top_k * 2)
        sparse = [(r.content, r.score) for r in sparse_results]

        # ── fusion ───────────────────────────────────────
        fused = fuse(dense, sparse, top_k=query.top_k * 2)
        candidates = [f.content for f in fused]

        # ── rerank ───────────────────────────────────────
        reranked = False
        if query.use_reranker and candidates:
            scores = await self._reranker.rerank(clean, candidates)
            paired = sorted(
                zip(candidates, scores),
                key=lambda x: x[1],
                reverse=True,
            )
            candidates = [c for c, _ in paired]
            reranked = True

        documents = [
            RetrievedDocument(content=c, score=fused[i].score if i < len(fused) else 0.0)
            for i, c in enumerate(candidates[:query.top_k])
        ]

        # ── cache result ─────────────────────────────────
        await self._query_cache.set(
            clean, query.user_id,
            [{"content": d.content, "score": d.score} for d in documents],
        )

        return RetrievalResult(query=clean, documents=documents, reranked=reranked)