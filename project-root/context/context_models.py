from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextChunk:
    """
    A single retrieved memory chunk with full provenance.

    Fields:
        content   — the raw text passed to the prompt.
        score     — primary ranking score (rerank > rrf > similarity).
        source    — origin: 'memory' | 'bm25' | 'hybrid'.
        metadata  — document-level attributes: doc_id, mem_type, source_url,
                    created_at, credibility, etc. Set at index time, stable.
        retrieval — process-level attributes: bm25_score, rrf_score,
                    dense_rank, sparse_rank, rerank_score, geo_score, etc.
                    Set during retrieval pipeline, describes how the chunk
                    was found and ranked. Never mix with metadata.
    """
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)   # document attributes
    retrieval: dict = field(default_factory=dict)  # pipeline attributes


@dataclass(frozen=True)
class ContextBlock:
    """
    Assembled context ready for serialization.

    chunks      — ordered list of ContextChunks after truncation.
    total_chars — total character count of accepted chunks + separators.
    truncated   — True if char budget was hit before exhausting all chunks.
    """
    chunks: list[ContextChunk]
    total_chars: int
    truncated: bool = False