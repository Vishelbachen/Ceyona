from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# =========================
# CONTEXT REQUEST
# =========================
@dataclass(frozen=True)
class ContextRequest:
    """
    ROLE:
    - input contract for context assembler

    SOURCE:
    - orchestrator
    - retrieval layer output
    """

    user_query: str
    retrieved_items: List[Dict[str, Any]]
    max_tokens: int = 4000


# =========================
# CONTEXT CHUNK
# =========================
@dataclass(frozen=True)
class ContextChunk:
    """
    ROLE:
    - atomic unit of context passed to LLM

    RULE:
    - no reasoning
    - no summarization logic inside
    """

    text: str
    source_id: Optional[int] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# =========================
# FINAL CONTEXT PAYLOAD
# =========================
@dataclass(frozen=True)
class ContextPayload:
    """
    ROLE:
    - final structured input for LLM layer

    USED BY:
    - llm.prompt_engine
    """

    system_prompt: str
    user_prompt: str
    context_chunks: List[ContextChunk]
    total_tokens_estimate: Optional[int] = None


# =========================
# CONTEXT METADATA (OBSERVABILITY ONLY)
# =========================
@dataclass(frozen=True)
class ContextMeta:
    """
    ROLE:
    - debugging + tracing only
    """

    truncated: bool
    retrieval_items_count: int
    context_chunks_count: int