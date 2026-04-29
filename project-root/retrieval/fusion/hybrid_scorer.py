from dataclasses import dataclass

_DENSE_WEIGHT = 0.7
_SPARSE_WEIGHT = 0.3


@dataclass(frozen=True)
class FusionResult:
    content: str
    score: float


def fuse(
    dense: list[tuple[str, float]],
    sparse: list[tuple[str, float]],
    top_k: int = 5,
) -> list[FusionResult]:
    """
    Reciprocal Rank Fusion (RRF) + weighted combination.
    dense/sparse: list of (content, score) tuples.
    Pure function. No I/O.
    """
    scores: dict[str, float] = {}

    for content, score in dense:
        scores[content] = scores.get(content, 0.0) + score * _DENSE_WEIGHT

    for content, score in sparse:
        scores[content] = scores.get(content, 0.0) + score * _SPARSE_WEIGHT

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [FusionResult(content=c, score=s) for c, s in ranked[:top_k]]