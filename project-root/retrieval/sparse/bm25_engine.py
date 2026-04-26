from __future__ import annotations

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import re


# =========================
# BM25 SPARSE ENGINE
# =========================
class BM25Engine:
    """
    ROLE:
    - classic sparse retrieval (BM25)
    - keyword-based document ranking

    STRICT RULES:
    - NO embeddings
    - NO semantics
    - NO reranking
    - NO LLM usage
    """

    def __init__(self, documents: List[Dict[str, Any]]):

        self.documents = documents
        self.tokenized_corpus = [
            self._tokenize(doc["text"]) for doc in documents
        ]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

    # =========================
    # TOKENIZATION (PURE)
    # =========================
    def _tokenize(self, text: str) -> List[str]:

        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = text.split()

        return tokens

    # =========================
    # SEARCH
    # =========================
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:

        query_tokens = self._tokenize(query)

        scores = self.bm25.get_scores(query_tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = []

        for idx, score in ranked:
            results.append({
                "id": idx,
                "score": float(score),
                "source": "sparse",
            })

        return results

    # =========================
    # DEBUG ONLY
    # =========================
    def explain(self, query: str) -> Dict[str, Any]:

        return {
            "query": query,
            "tokens": self._tokenize(query),
            "corpus_size": len(self.documents),
        }