import logging

from llm.hf_client import BGE_RERANKER, hf_client

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
    ) -> list[tuple[str, float]]:
        """
        Returns list of (content, score) sorted by score descending.
        """
        if not candidates:
            return []
        try:
            scores = await hf_client.rerank(
                query=query,
                candidates=candidates,
                model=BGE_RERANKER,
            )
            pairs = list(zip(candidates, scores))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs
        except Exception as exc:
            logger.error("CrossEncoder.rerank failed", extra={"error": str(exc)})
            # fallback: return unranked with score 0
            return [(c, 0.0) for c in candidates]


cross_encoder = CrossEncoder()