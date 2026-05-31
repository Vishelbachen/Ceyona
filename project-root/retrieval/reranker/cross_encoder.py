from __future__ import annotations

import logging

from llm.hf_client import BGE_RERANKER, hf_client
from retrieval.query_preprocessor import geo_relevance_score

logger = logging.getLogger(__name__)


class CrossEncoder:
    """
    Cross-encoder reranker using BGE-reranker-large.
    Scores only. No generation. No decision authority.
    """

    async def rerank(
        self,
        query: str,
        candidates: list[str],
        lang: str = "en",
    ) -> list[tuple[str, float]]:
        """
        Returns list of (content, score) sorted by score descending.

        The model score is kept as the primary signal. Geo affinity is used as a
        deterministic secondary boost for location-sensitive queries.
        """
        if not candidates:
            return []

        def _fallback_rank() -> list[tuple[str, float]]:
            ranked: list[tuple[str, float]] = []
            for content in candidates:
                geo_score = geo_relevance_score(query, content, lang=lang)
                text = content.casefold()
                token_boost = 0.0
                if query:
                    query_terms = set(query.casefold().split())
                    candidate_terms = set(text.split())
                    if query_terms and candidate_terms:
                        token_boost = len(query_terms & candidate_terms) / max(len(query_terms | candidate_terms), 1)
                score = (geo_score * 0.65) + (token_boost * 0.35)
                ranked.append((content, score))
            ranked.sort(key=lambda x: x[1], reverse=True)
            return ranked

        try:
            scores = await hf_client.rerank(
                query=query,
                candidates=candidates,
                model=BGE_RERANKER,
            )
            pairs = list(zip(candidates, scores))
            adjusted: list[tuple[str, float]] = []
            for content, raw_score in pairs:
                geo_score = geo_relevance_score(query, content, lang=lang)
                adjusted_score = float(raw_score) + (geo_score * 0.15)
                adjusted.append((content, adjusted_score))
            adjusted.sort(key=lambda x: x[1], reverse=True)
            return adjusted
        except Exception as exc:
            logger.error("CrossEncoder.rerank failed", extra={"error": str(exc)})
            return _fallback_rank()


cross_encoder = CrossEncoder()