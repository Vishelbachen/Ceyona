import logging
import math
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BM25Result:
    content: str
    score: float


class BM25Engine:
    """
    In-memory BM25 sparse retrieval.
    Deterministic. No I/O. No state beyond corpus.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._corpus: list[str] = []
        self._tf: list[Counter] = []
        self._df: Counter = Counter()
        self._avg_len: float = 0.0

    def index(self, documents: list[str]) -> None:
        self._corpus = documents
        tokenized = [doc.lower().split() for doc in documents]
        self._tf = [Counter(t) for t in tokenized]
        self._df = Counter()
        for t in tokenized:
            for term in set(t):
                self._df[term] += 1
        lengths = [len(t) for t in tokenized]
        self._avg_len = sum(lengths) / max(len(lengths), 1)

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        if not self._corpus:
            return []

        terms = query.lower().split()
        n = len(self._corpus)
        scores: list[float] = []

        for i, tf in enumerate(self._tf):
            doc_len = sum(tf.values())
            score = 0.0
            for term in terms:
                if term not in tf:
                    continue
                df = self._df.get(term, 0)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf_val = tf[term]
                norm_tf = tf_val * (self.k1 + 1) / (
                    tf_val + self.k1 * (1 - self.b + self.b * doc_len / self._avg_len)
                )
                score += idf * norm_tf
            scores.append(score)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [
            BM25Result(content=self._corpus[i], score=s)
            for i, s in ranked[:top_k]
            if s > 0
        ]