import logging
import math
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_K1 = 1.5
_B = 0.75


@dataclass(frozen=True)
class BM25Result:
    content: str
    score: float


class BM25Engine:
    """
    In-memory BM25 sparse retrieval.
    Built from a corpus at init time.
    No I/O. No semantic inference.
    """

    def __init__(self, corpus: list[str]) -> None:
        self._corpus = corpus
        self._n = len(corpus)
        self._avgdl = 0.0
        self._tf: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}
        self._build()

    def _tokenize(self, text: str) -> list[str]:
        return text.lower().split()

    def _build(self) -> None:
        if not self._corpus:
            return

        df: dict[str, int] = defaultdict(int)
        tokenized = [self._tokenize(doc) for doc in self._corpus]
        self._avgdl = sum(len(t) for t in tokenized) / self._n

        for tokens in tokenized:
            tf: dict[str, float] = defaultdict(float)
            for tok in tokens:
                tf[tok] += 1
            self._tf.append(dict(tf))
            for tok in set(tokens):
                df[tok] += 1

        for term, freq in df.items():
            self._idf[term] = math.log((self._n - freq + 0.5) / (freq + 0.5) + 1)

    def search(self, query: str, top_k: int = 5) -> list[BM25Result]:
        if not self._corpus:
            return []

        tokens = self._tokenize(query)
        scores: list[float] = []

        for i, doc_tf in enumerate(self._tf):
            dl = sum(doc_tf.values())
            score = 0.0
            for tok in tokens:
                if tok not in self._idf:
                    continue
                tf = doc_tf.get(tok, 0.0)
                numerator = tf * (_K1 + 1)
                denominator = tf + _K1 * (1 - _B + _B * dl / self._avgdl)
                score += self._idf[tok] * numerator / denominator
            scores.append(score)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [
            BM25Result(content=self._corpus[i], score=s)
            for i, s in ranked[:top_k]
            if s > 0
        ]