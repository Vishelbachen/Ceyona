import logging

from contracts.retrieval_contracts import RetrievalDocument
from llm.hf_client import BGE_LARGE, BGE_SMALL, hf_client

logger = logging.getLogger(__name__)


async def retrieve_dense(
    query: str,
    user_id: str,
    top_k: int = 10,
    embedding_type: str = "large",
) -> tuple[list[RetrievalDocument], int]:
    """
    Generate query embedding and search memory store.
    Returns (documents, embedding_tokens).
    """
    model = BGE_LARGE if embedding_type == "large" else BGE_SMALL

    try:
        vectors = await hf_client.embed([query], model=model)
        if not vectors:
            return [], 0

        embedding = vectors[0]
        # tokens estimate: query chars / 4
        tokens = max(1, len(query) // 4)

        from memory.supabase_store import SupabaseStore
        from supabase import create_client
        from app.settings import settings
        supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        store = SupabaseStore(supabase)

        records = await store.similarity_search(
            embedding=embedding,
            user_id=user_id,
            limit=top_k,
        )

        docs = [
            RetrievalDocument(
                content=r.content,
                score=r.importance,
                source="memory",
                metadata=r.metadata,
            )
            for r in records
        ]
        return docs, tokens

    except Exception as exc:
        logger.warning("bge_engine failed", extra={"error": str(exc)})
        return [], 0