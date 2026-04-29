import logging

from llm.hf_client import hf_client
from retrieval.cache.rerank_cache import RerankCache

logger = logging.getLogger(__name__)


class CrossEncoder:
    """
    Reranks candidates using BGE reranker.
    Scoring only. No decision authority.
    """

    def __init__(self, rerank_cache: RerankCache) -> None:
        self._cache = rerank_cache

    async def rerank(
        self,
        query: str,
        candidates: list[str],
    ) -> list[float]:
        if not candidates:
            return []

        cached = await self._cache.get(query, candidates)
        if cached is not None:
            return cached

        try:
            scores = await hf_client.rerank(query, candidates)
            await self._cache.set(query, candidates, scores)
            return scores
        except Exception as exc:
            logger.error("CrossEncoder rerank failed", extra={"error": str(exc)})
            return [0.0] * len(candidates)