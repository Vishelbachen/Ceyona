from typing import Any, Dict, List, Optional


class VectorMemory:
    """
    AI Platform v4.7 — Vector Memory Store

    RESPONSIBILITY:
    - Store and retrieve embedding vectors
    - Provide similarity-based lookup (raw results only)
    - Serve retrieval_engine layer

    STRICT RULES:
    - No semantic interpretation
    - No ranking logic beyond vector similarity output
    - No LLM usage
    - No decision-making
    - No business logic
    """

    def __init__(self, embedding_client: Any):
        self.embedding_client = embedding_client
        self._index: List[Dict[str, Any]] = []

    def add(
        self,
        record_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stores vectorized representation of text.
        """

        embedding = self.embedding_client.embed(text)

        entry = {
            "id": record_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        }

        self._index.append(entry)

        return {"status": "stored", "id": record_id}

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Returns raw nearest neighbors (no interpretation).
        """

        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b + 1e-8)

        scored = []

        for item in self._index:
            score = cosine_similarity(query_embedding, item["embedding"])
            scored.append({**item, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)

        return scored[:top_k]

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Returns full vector index (debug / admin only).
        """
        return self._index