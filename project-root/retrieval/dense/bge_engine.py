from typing import Any, Dict, List, Optional
import math


class BGEEngine:
    """
    AI Platform v4.7 — Dense Retrieval Engine (BGE)

    RESPONSIBILITY:
    - Perform embedding-based similarity search
    - Compute vector similarity scores
    - Return ranked candidate documents based on cosine similarity

    STRICT RULES:
    - No semantic interpretation
    - No query rewriting
    - No LLM reasoning
    - No retrieval orchestration
    - No fusion logic
    """

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Stores documents with embeddings.
        Each document must include 'embedding': List[float]
        """

        self.documents = documents

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Computes cosine similarity between two vectors.
        """

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns top-k most similar documents.
        """

        scored = []

        for doc in self.documents:
            doc_embedding = doc.get("embedding", [])

            score = self._cosine_similarity(query_embedding, doc_embedding)

            scored.append({
                "id": doc.get("id"),
                "score": score,
                "content": doc.get("content"),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        return scored[:top_k]