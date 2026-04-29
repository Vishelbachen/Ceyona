from contracts.retrieval_contracts import RetrievalDocument

_DENSE_WEIGHT = 0.7
_SPARSE_WEIGHT = 0.3


def fuse(
    dense: list[RetrievalDocument],
    sparse: list[RetrievalDocument],
    top_k: int = 10,
) -> list[RetrievalDocument]:
    """
    Reciprocal Rank Fusion of dense + sparse results.
    Pure function. No I/O. No inference.
    """
    scores: dict[str, float] = {}
    content_map: dict[str, RetrievalDocument] = {}

    for rank, doc in enumerate(dense):
        key = doc.content[:200]
        scores[key] = scores.get(key, 0.0) + _DENSE_WEIGHT * (1.0 / (rank + 1))
        content_map[key] = doc

    for rank, doc in enumerate(sparse):
        key = doc.content[:200]
        scores[key] = scores.get(key, 0.0) + _SPARSE_WEIGHT * (1.0 / (rank + 1))
        if key not in content_map:
            content_map[key] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    result = []
    for key, score in ranked[:top_k]:
        doc = content_map[key]
        result.append(RetrievalDocument(
            content=doc.content,
            score=score,
            source=doc.source,
            metadata=doc.metadata,
        ))
    return result