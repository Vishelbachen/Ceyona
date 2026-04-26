from __future__ import annotations

from typing import List, Dict, Any
from collections import defaultdict


# =========================
# HYBRID SCORER (BM25 + DENSE)
# =========================
class HybridScorer:
    """
    ROLE:
    - merge sparse (BM25) + dense (BGE) results
    - produce unified ranked list

    STRICT RULES:
    - NO reranking logic
    - NO ML blending
    - NO semantic interpretation
    - ONLY deterministic score fusion
    """

    def __init__(
        self,
        sparse_weight: float = 0.4,
        dense_weight: float = 0.6,
    ):

        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight

    # =========================
    # MAIN FUSION METHOD
    # =========================
    def fuse(
        self,
        sparse_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        score_map = defaultdict(lambda: {
            "id": None,
            "score": 0.0,
            "sources": set(),
        })

        # -------------------------
        # ADD SPARSE (BM25)
        # -------------------------
        for item in sparse_results:
            doc_id = item["id"]

            score_map[doc_id]["id"] = doc_id
            score_map[doc_id]["score"] += (
                item.get("score", 0.0) * self.sparse_weight
            )
            score_map[doc_id]["sources"].add("sparse")

        # -------------------------
        # ADD DENSE (BGE)
        # -------------------------
        for item in dense_results:
            doc_id = item["id"]

            score_map[doc_id]["id"] = doc_id
            score_map[doc_id]["score"] += (
                item.get("score", 0.0) * self.dense_weight
            )
            score_map[doc_id]["sources"].add("dense")

        # -------------------------
        # FINALIZE
        # -------------------------
        merged = []

        for value in score_map.values():
            merged.append({
                "id": value["id"],
                "score": float(value["score"]),
                "sources": list(value["sources"]),
            })

        # deterministic sort ONLY
        merged.sort(key=lambda x: x["score"], reverse=True)

        return merged