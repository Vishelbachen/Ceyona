import logging
import math
from collections import Counter

from contracts.retrieval_contracts import RetrievalDocument

logger = logging.getLogger(__name__)

# In-memory BM25 over a small static corpus.
# Replace corpus with DB-backed fetch when scale requires it.
_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _bm25_score(
    query_terms: list[str],
    doc_terms: list[str],
    corpus_size: int,
    avg_doc_len: float,
    df: dict[str, int],
) -> float:
    doc_len = len(doc_terms)
    term_freq = Counter(doc_terms)
    score = 0.0
    for term in query_terms:
        if term not in term_freq:
            continue
        tf = term_freq[term]
        n_docs_with_term = df.get(term, 0)
        if n_docs_with_term == 0:
            continue
        idf = math.log((corpus_size - n_docs_with_term + 0.5) / (n_docs_with_term + 0.5) + 1)
        tf_norm = (tf * (_K1 + 1)) / (tf + _K1 * (1 - _B + _B * doc_len / max(avg_doc_len, 1)))
        score += idf * tf_norm
    return score


async def retrieve_sparse(
    query: str,
    corpus: list[str] | None = None,
    top_k: int = 10,
) -> list[RetrievalDocument]:
    """
    BM25 sparse retrieval over provided corpus.
    Returns ranked RetrievalDocument list.
    If no corpus provided, returns empty list (retrieval_engine handles fallback).
    """
    if not corpus:
        return []

    query_terms = _tokenize(query)
    tokenized_corpus = [_tokenize(doc) for doc in corpus]
    avg_doc_len = sum(len(d) for d in tokenized_corpus) / max(len(tokenized_corpus), 1)

    df: dict[str, int] = {}
    for doc_terms in tokenized_corpus:
        for term in set(doc_terms):
            df[term] = df.get(term, 0) + 1

    scored = []
    for i, (doc_text, doc_terms) in enumerate(zip(corpus, tokenized_corpus)):
        score = _bm25_score(
            query_terms, doc_terms,
            len(corpus), avg_doc_len, df,
        )
        scored.append(RetrievalDocument(content=doc_text, score=score, source="bm25"))

    scored.sort(key=lambda d: d.score, reverse=True)
    return scored[:top_k]