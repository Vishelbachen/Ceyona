from typing import Any, Dict, List, Optional
from collections import defaultdict
import math


class BM25Engine:
    """
    AI Platform v4.7 — BM25 Sparse Retrieval Engine

    RESPONSIBILITY:
    - Perform lexical (keyword-based) document scoring
    - Provide BM25 ranking over indexed documents

    STRICT RULES:
    - No semantic understanding
    - No query rewriting
    - No LLM / memory / retrieval orchestration
    - No decision-making beyond formula scoring
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.index: List[Dict[str, Any]] = []
        self.doc_freq = defaultdict(int)
        self.doc_lengths = {}
        self.avg_doc_length = 0.0

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Adds documents to index (no preprocessing logic).
        """

        self.index = documents
        total_length = 0

        for doc in documents:
            doc_id = doc["id"]
            content = doc["content"]
            tokens = content.lower().split()

            self.doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)

            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freq[token] += 1

        if documents:
            self.avg_doc_length = total_length / len(documents)

    def _idf(self, term: str, total_docs: int) -> float:
        """
        Inverse document frequency.
        """

        df = self.doc_freq.get(term, 0)
        return math.log((total_docs - df + 0.5) / (df + 0.5) + 1)

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Executes BM25 ranking over indexed documents.
        """

        query_tokens = query.lower().split()
        scores = []

        for doc in self.index:
            doc_id = doc["id"]
            content_tokens = doc["content"].lower().split()

            score = 0.0

            for term in query_tokens:
                if term not in content_tokens:
                    continue

                tf = content_tokens.count(term)
                idf = self._idf(term, len(self.index))

                doc_len = self.doc_lengths.get(doc_id, 1)

                score += idf * (
                    (tf * (self.k1 + 1)) /
                    (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                )

            scores.append({
                "id": doc_id,
                "score": score,
                "content": doc["content"],
            })

        scores.sort(key=lambda x: x["score"], reverse=True)

        return scores[:top_k]