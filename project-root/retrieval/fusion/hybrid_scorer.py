from dataclasses import dataclass


@dataclass
class FusedResult:
    content: str
    score: float
    source: str = ""


def reciprocal_rank_fusion(
    sparse_results: list[tuple[str, float]],
    dense_results: list[tuple[str, float]],
    k: int = 60,
    sparse_weight: float = 0.4,
    dense_weight: float = 0.6,
) -> list[FusedResult]:
    """
    Reciprocal Rank Fusion of sparse (BM25) and dense (BGE) results.
    Pure function. No I/O.
    """
    scores: dict[str, float] = {}

    for rank, (content, _) in enumerate(sparse_results):
        scores[content] = scores.get(content, 0.0) + sparse_weight / (k + rank + 1)

    for rank, (content, _) in enumerate(dense_results):
        scores[content] = scores.get(content, 0.0) + dense_weight / (k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [FusedResult(content=c, score=s) for c, s in ranked]