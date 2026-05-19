import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "memory"


@dataclass
class MemoryEntry:
    user_id: str
    content: str
    embedding: list[float]
    mem_type: str = "general"
    importance: float = 1.0
    metadata: dict | None = None


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    user_id: str
    content: str
    mem_type: str
    importance: float
    metadata: dict
    created_at: str
    source_url: str | None = None  # §5.3: provenance for retrieval-originated records


class SupabaseStore:
    """
    Raw storage layer for memory entries.
    Stores and retrieves records from Supabase.
    No semantic logic. No ranking. Storage only.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def insert(self, entry: MemoryEntry) -> bool:
        """Insert a new memory entry with embedding."""
        try:
            self._db.table(_TABLE).insert({
                "user_id": entry.user_id,
                "content": entry.content,
                "embedding": entry.embedding,
                "mem_type": entry.mem_type,
                "importance": entry.importance,
                "metadata": entry.metadata or {},
            }).execute()
            logger.info("Memory inserted", extra={
                "user_id": entry.user_id,
                "mem_type": entry.mem_type,
            })
            return True
        except Exception as exc:
            logger.error("Memory insert failed", extra={"error": str(exc)})
            return False

    async def fetch_by_user(
        self,
        user_id: str,
        limit: int = 20,
        mem_type: str | None = None,
    ) -> list[MemoryRecord]:
        """Fetch recent memory records for a user."""
        try:
            query = (
                self._db.table(_TABLE)
                .select("id, user_id, content, mem_type, importance, metadata, created_at, source_url")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            if mem_type:
                query = query.eq("mem_type", mem_type)

            result = query.execute()
            return [
                MemoryRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    content=row["content"],
                    mem_type=row["mem_type"],
                    importance=row["importance"],
                    metadata=row["metadata"] or {},
                    created_at=row["created_at"],
                    source_url=row.get("source_url"),
                )
                for row in (result.data or [])
            ]
        except Exception as exc:
            logger.error("Memory fetch failed", extra={"error": str(exc)})
            return []

    async def delete_by_user(self, user_id: str) -> bool:
        """Delete all memory entries for a user."""
        try:
            self._db.table(_TABLE).delete().eq("user_id", user_id).execute()
            logger.info("Memory deleted", extra={"user_id": user_id})
            return True
        except Exception as exc:
            logger.error("Memory delete failed", extra={"error": str(exc)})
            return False

    async def similarity_search(
        self,
        embedding: list[float],
        user_id: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[MemoryRecord]:
        """
        Vector similarity search via pgvector RPC.
        Calls match_memory Postgres function.
        """
        try:
            result = self._db.rpc("match_memory", {
                "query_embedding": embedding,
                "match_user_id": user_id,
                "match_threshold": threshold,
                "match_count": limit,
            }).execute()

            return [
                MemoryRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    content=row["content"],
                    mem_type=row["mem_type"],
                    importance=row.get("importance", 1.0),
                    metadata=row.get("metadata") or {},
                    created_at=row.get("created_at", ""),
                    source_url=row.get("source_url"),
                )
                for row in (result.data or [])
            ]
        except Exception as exc:
            logger.error("Similarity search failed", extra={"error": str(exc)})
            return []