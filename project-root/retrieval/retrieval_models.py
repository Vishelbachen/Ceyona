from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryVector:
    text: str
    embedding: list[float]
    model: str


@dataclass(frozen=True)
class RetrievalMetadata:
    """
    Process-level attributes describing how a candidate was found and ranked.

    Distinct from document-level metadata (doc_id, mem_type, source_url)
    which lives in ScoredCandidate.metadata.

    Fields are Optional so each retrieval stage only fills what it knows:
      - dense stage fills dense_score
      - sparse (BM25) stage fills sparse_score
      - RRF fusion fills rrf_score, geo_score, dense_rank, sparse_rank
      - reranker fills rerank_score
    """
    dense_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float | None = None
    geo_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rerank_score: float | None = None


@dataclass(frozen=True)
class ScoredCandidate:
    """
    A single retrieval result with full provenance.

    Lives in the retrieval layer only. Converted to ContextChunk
    via context_mapper.to_context_chunks() before entering the context layer.

    Fields:
        content   — raw text of the retrieved document.
        score     — primary ranking score (rerank > rrf > similarity).
        source    — retrieval origin: 'memory' | 'bm25' | 'hybrid'.
        metadata  — document attributes: doc_id, mem_type, source_url, etc.
                    Stable, set at index time.
        retrieval — process attributes via RetrievalMetadata.
                    Set during pipeline, never mix with metadata.
    """
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)
    retrieval: RetrievalMetadata = field(default_factory=RetrievalMetadata)