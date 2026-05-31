from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from retrieval.query_preprocessor import geo_relevance_score


@dataclass(frozen=True)
class FusedResult:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


def _as_content_score(item: object) -> tuple[str, float]:
    if isinstance(item, FusedResult):
        return item.content, item.score
    if isinstance(item, tuple):
        if len(item) >= 2:
            return str(item[0]), float(item[1])
        if len(item) == 1:
            return str(item[0]), 0.0
    return str(item), 0.0


def reciprocal_rank_fusion(
    sparse_results: list[tuple[str, float]] | list[FusedResult],
    dense_results: list[tuple[str, float]] | list[FusedResult],
    k: int = 60,
    sparse_weight: float = 0.4,
    dense_weight: float = 0.6,
    query: str = "",
    lang: str = "en",
) -> list[FusedResult]:
    """
    Reciprocal Rank Fusion of sparse and dense results.

    The function remains deterministic and pure. Query-aware geo relevance is
    used only as a secondary boost when a geo-sensitive query is supplied.
    """
    scores: dict[str, float] = {}
    provenance: dict[str, dict[str, float]] = {}

    for rank, item in enumerate(sparse_results):
        content, _ = _as_content_score(item)
        scores[content] = scores.get(content, 0.0) + sparse_weight / (k + rank + 1)
        provenance.setdefault(content, {})["sparse_rank"] = float(rank + 1)

    for rank, item in enumerate(dense_results):
        content, _ = _as_content_score(item)
        scores[content] = scores.get(content, 0.0) + dense_weight / (k + rank + 1)
        provenance.setdefault(content, {})["dense_rank"] = float(rank + 1)

    fused: list[FusedResult] = []
    geo_sensitive = bool(query.strip())
    for content, base_score in scores.items():
        geo_score = geo_relevance_score(query, content, lang=lang) if geo_sensitive else 0.0
        total = base_score + (geo_score * 0.05)
        fused.append(
            FusedResult(
                content=content,
                score=total,
                source="hybrid",
                metadata={
                    "rrf_score": round(base_score, 6),
                    "geo_score": round(geo_score, 3),
                    **provenance.get(content, {}),
                },
            )
        )

    return sorted(fused, key=lambda item: item.score, reverse=True)