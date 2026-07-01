"""
context/context_mapper.py

Boundary between the retrieval layer and the context layer.

This is the only file that knows about both ScoredCandidate (retrieval)
and ContextChunk (context). All other context-layer code receives
ContextChunk and never imports from retrieval/.
"""
from context.context_models import ContextChunk
from retrieval.retrieval_models import ScoredCandidate


def to_context_chunks(candidates: list[ScoredCandidate]) -> list[ContextChunk]:
    """
    Convert retrieval results into context-layer chunks.

    Copies document metadata as-is. Retrieval process metadata
    (scores, ranks) is intentionally dropped here — it was used
    for ranking decisions inside retrieval_engine and is not needed
    by assembler or serializer.

    If citation/attribution features are added later, extend ContextChunk
    and map the relevant RetrievalMetadata fields here.
    """
    return [
        ContextChunk(
            content=c.content,
            score=c.score,
            source=c.source,
            metadata=c.metadata,
        )
        for c in candidates
        if c.content.strip()
    ]