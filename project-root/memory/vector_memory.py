import logging
from dataclasses import dataclass

from llm.hf_client import BGE_LARGE, BGE_SMALL, hf_client
from memory.supabase_store import MemoryEntry, MemoryRecord, SupabaseStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorSearchResult:
    content: str
    mem_type: str
    importance: float
    metadata: dict
    source_url: str | None = None
    similarity: float = 1.0


class VectorMemory:
    """
    Semantic memory layer.
    Generates embeddings via HF and stores/retrieves via SupabaseStore.
    No interpretation. No ranking beyond cosine similarity.
    """

    def __init__(self, store: SupabaseStore) -> None:
        self._store = store

    async def remember(
        self,
        user_id: str,
        content: str,
        mem_type: str = "general",
        importance: float = 1.0,
        metadata: dict | None = None,
        use_fast: bool = False,
    ) -> bool:
        """
        Generate embedding and store memory entry.
        use_fast=True → bge-small (lower latency, lower cost).
        """
        model = BGE_SMALL if use_fast else BGE_LARGE
        try:
            vectors = await hf_client.embed([content], model=model)
            if not vectors:
                logger.error("Empty embedding returned")
                return False

            embedding = vectors[0]
            entry = MemoryEntry(
                user_id=user_id,
                content=content,
                embedding=embedding,
                mem_type=mem_type,
                importance=importance,
                metadata=metadata or {},
                source_url=(metadata or {}).get("source_url"),
            )
            return await self._store.insert(entry)

        except Exception as exc:
            logger.error("remember failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False

    async def recall(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
        use_fast: bool = False,
    ) -> list[VectorSearchResult]:
        """
        Embed query and retrieve semantically similar memories.
        Returns ranked results by cosine similarity.
        """
        model = BGE_SMALL if use_fast else BGE_LARGE
        try:
            vectors = await hf_client.embed([query], model=model)
            if not vectors:
                return []

            embedding = vectors[0]
            records: list[MemoryRecord] = await self._store.similarity_search(
                embedding=embedding,
                user_id=user_id,
                limit=limit,
                threshold=threshold,
            )

            return [
                VectorSearchResult(
                    content=r.content,
                    mem_type=r.mem_type,
                    importance=r.importance,
                    metadata=r.metadata,
                    source_url=r.source_url,
                    similarity=r.similarity,
                )
                for r in records
            ]

        except Exception as exc:
            logger.error("recall failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return []

    async def forget(self, user_id: str) -> bool:
        """Delete all memories for a user."""
        return await self._store.delete_by_user(user_id)