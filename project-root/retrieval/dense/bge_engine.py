import logging

from contracts.retrieval_contracts import RetrievedDocument
from llm.hf_client import BGE_LARGE, BGE_SMALL, hf_client
from retrieval.cache.embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)


class BGEEngine:
    """
    Dense retrieval via BGE embeddings.
    Generates query embedding only — document embeddings stored in Supabase.
    """

    def __init__(self, embedding_cache: EmbeddingCache) -> None:
        self._cache = embedding_cache

    async def embed_query(
        self,
        query: str,
        use_fast: bool = False,
    ) -> list[float]:
        model = BGE_SMALL if use_fast else BGE_LARGE

        cached = await self._cache.get(query, model)
        if cached is not None:
            return cached

        try:
            vectors = await hf_client.embed([query], model=model)
            embedding = vectors[0] if vectors else []
            if embedding:
                await self._cache.set(query, model, embedding)
            return embedding
        except Exception as exc:
            logger.error("BGE embed failed", extra={"error": str(exc)})
            return []