from __future__ import annotations

from typing import List, Dict, Any, Optional

from retrieval.dense.bge_engine import BGEEngine
from retrieval.sparse.bm25_engine import BM25Engine
from retrieval.fusion.hybrid_scorer import HybridScorer
from retrieval.reranker.cross_encoder import CrossEncoderReranker
from retrieval.cache.query_cache import QueryCache


# =========================
# RETRIEVAL ENGINE (ONLY ENTRY POINT)
# =========================
class RetrievalEngine:
    """
    ROLE:
    - single entry point for ALL retrieval
    - orchestrates sparse + dense + rerank
    - returns ranked documents ONLY

    STRICT RULES:
    - NO interpretation
    - NO summarization
    - NO LLM usage
    - NO decision making
    - NO context understanding
    """

    def __init__(
        self,
        bm25: BM25Engine,
        dense: BGEEngine,
        scorer: HybridScorer,
        reranker: CrossEncoderReranker,
        cache: QueryCache,
    ):

        self.bm25 = bm25
        self.dense = dense
        self.scorer = scorer
        self.reranker = reranker
        self.cache = cache

    # =========================
    # MAIN ENTRY
    # =========================
    def search(
        self,
        query: str,
        top_k: int = 10,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:

        # -------------------------
        # 1. CACHE CHECK
        # -------------------------
        if use_cache:
            cached = self.cache.get(query, top_k)
            if cached is not None:
                return cached

        # -------------------------
        # 2. SPARSE RETRIEVAL (BM25)
        # -------------------------
        sparse_results = self.bm25.search(query, top_k=top_k * 2)

        # -------------------------
        # 3. DENSE RETRIEVAL (EMBEDDINGS)
        # -------------------------
        dense_results = self.dense.search(query, top_k=top_k * 2)

        # -------------------------
        # 4. HYBRID FUSION
        # -------------------------
        fused = self.scorer.fuse(
            sparse_results=sparse_results,
            dense_results=dense_results,
        )

        # -------------------------
        # 5. RERANKING (CROSS-ENCODER)
        # -------------------------
        reranked = self.reranker.rerank(
            query=query,
            documents=fused,
            top_k=top_k,
        )

        # -------------------------
        # 6. CACHE STORE
        # -------------------------
        if use_cache:
            self.cache.set(query, top_k, reranked)

        return reranked

    # =========================
    # DEBUG / INSPECTION ONLY
    # =========================
    def explain_pipeline(self, query: str) -> Dict[str, Any]:

        return {
            "query": query,
            "bm25": self.bm25.search(query, top_k=5),
            "dense": self.dense.search(query, top_k=5),
        }