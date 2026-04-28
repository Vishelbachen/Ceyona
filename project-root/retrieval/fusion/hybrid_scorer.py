from typing import Any, Dict, List


class HybridScorer:
    """
    AI Platform v4.7 — Hybrid Scoring (Fusion Layer)

    RESPONSIBILITY:
    - Combine scores from multiple retrieval sources
    - Normalize and aggregate ranking signals
    - Produce unified relevance score

    STRICT RULES:
    - No semantic interpretation
    - No query understanding
    - No decision-making logic
    - No LLM / memory / reasoning usage
    - No final ranking authority (reranker is final)
    """

    def __init__(
        self,
        bm25_weight: float = 0.3,
        dense_weight: float = 0.5,
        web_weight: float = 0.2,
    ):
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.web_weight = web_weight

    def _safe_score(self, value: float) -> float:
        """
        Ensures score is within [0, 1] range.
        """

        if value is None:
            return 0.0

        return max(0.0, min(1.0, value))

    def fuse(
        self,
        bm25_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
        web_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Combines multiple retrieval sources into unified score list.
        """

        fused: Dict[str, Dict[str, Any]] = {}

        # =========================
        # BM25 SCORES
        # =========================
        for item in bm25_results:
            doc_id = item["id"]

            fused.setdefault(doc_id, {
                "id": doc_id,
                "content": item.get("content", ""),
                "bm25": 0.0,
                "dense": 0.0,
                "web": 0.0,
            })

            fused[doc_id]["bm25"] = self._safe_score(item.get("score", 0.0))

        # =========================
        # DENSE SCORES
        # =========================
        for item in dense_results:
            doc_id = item["id"]

            fused.setdefault(doc_id, {
                "id": doc_id,
                "content": item.get("content", ""),
                "bm25": 0.0,
                "dense": 0.0,
                "web": 0.0,
            })

            fused[doc_id]["dense"] = self._safe_score(item.get("score", 0.0))

        # =========================
        # WEB SCORES
        # =========================
        for item in web_results:
            doc_id = item.get("id") or item.get("url")

            fused.setdefault(doc_id, {
                "id": doc_id,
                "content": item.get("content", item.get("snippet", "")),
                "bm25": 0.0,
                "dense": 0.0,
                "web": 0.0,
            })

            fused[doc_id]["web"] = self._safe_score(item.get("score", 0.0))

        # =========================
        # FINAL SCORE (LINEAR FUSION)
        # =========================
        results = []

        for doc in fused.values():
            score = (
                doc["bm25"] * self.bm25_weight +
                doc["dense"] * self.dense_weight +
                doc["web"] * self.web_weight
            )

            results.append({
                **doc,
                "fused_score": score,
            })

        return sorted(results, key=lambda x: x["fused_score"], reverse=True)