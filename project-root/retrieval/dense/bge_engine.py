from __future__ import annotations

from typing import List, Dict, Any

import numpy as np


# =========================
# BGE DENSE ENGINE
# =========================
class BGEEngine:
    """
    ROLE:
    - generate embeddings using BGE model
    - perform vector similarity search
    - return ranked dense candidates

    STRICT RULES:
    - NO reranking logic
    - NO hybrid fusion
    - NO query understanding
    - NO memory access
    """

    def __init__(self, model, index):
        """
        model → embedding model (e.g. BGE)
        index → vector store (FAISS / HNSW / custom)
        """
        self.model = model
        self.index = index

    # =========================
    # EMBEDDING GENERATION
    # =========================
    def embed(self, text: str) -> np.ndarray:

        """
        Convert text → vector embedding
        """

        vector = self.model.encode(text)

        return np.array(vector, dtype=np.float32)

    # =========================
    # VECTOR SEARCH
    # =========================
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:

        query_vector = self.embed(query)

        # ANN search in vector index
        scores, ids = self.index.search(query_vector, top_k)

        results = []

        for score, idx in zip(scores[0], ids[0]):
            results.append({
                "id": int(idx),
                "score": float(score),
                "source": "dense",
            })

        return results

    # =========================
    # DEBUG ONLY
    # =========================
    def explain(self, query: str) -> Dict[str, Any]:

        vec = self.embed(query)

        return {
            "query": query,
            "vector_dim": len(vec),
            "sample_values": vec[:5].tolist(),
        }