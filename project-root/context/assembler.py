from __future__ import annotations

from typing import List, Dict, Any

from contracts.context_contracts import (
    ContextRequest,
    ContextChunk,
    ContextPayload,
    ContextMeta,
)

from retrieval.contracts.retrieval_contracts import RetrievalItem


# =========================
# CONTEXT ASSEMBLER
# =========================
class ContextAssembler:
    """
    ROLE:
    - convert retrieval output → LLM-ready structured context
    - enforce token budget
    - preserve ranking order

    STRICT RULES:
    - NO reasoning
    - NO summarization intelligence
    - NO query interpretation
    - ONLY formatting + slicing + packing
    """

    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer  # optional external tokenizer

    # =========================
    # MAIN ENTRY
    # =========================
    def build(self, request: ContextRequest) -> ContextPayload:

        chunks, meta = self._build_chunks(
            request.retrieved_items,
            request.max_tokens,
        )

        system_prompt = self._build_system_prompt()
        user_prompt = request.user_query

        return ContextPayload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_chunks=chunks,
            total_tokens_estimate=self._estimate_tokens(chunks),
        )

    # =========================
    # CHUNK BUILDER
    # =========================
    def _build_chunks(
        self,
        items: List[Dict[str, Any]],
        max_tokens: int,
    ) -> tuple[List[ContextChunk], ContextMeta]:

        chunks: List[ContextChunk] = []
        used_tokens = 0

        for item in items:

            text = self._extract_text(item)
            tokens = self._count_tokens(text)

            # hard budget cut
            if used_tokens + tokens > max_tokens:
                break

            chunks.append(
                ContextChunk(
                    text=text,
                    source_id=item.get("id"),
                    score=item.get("score"),
                    metadata={
                        "sources": item.get("sources"),
                    },
                )
            )

            used_tokens += tokens

        meta = ContextMeta(
            truncated=len(chunks) < len(items),
            retrieval_items_count=len(items),
            context_chunks_count=len(chunks),
        )

        return chunks, meta

    # =========================
    # TEXT EXTRACTION
    # =========================
    def _extract_text(self, item: Dict[str, Any]) -> str:

        """
        NOTE:
        retrieval layer may not contain raw text,
        so this assumes upstream enrichment exists.
        """

        return item.get("text", f"doc_{item['id']}")

    # =========================
    # TOKEN ESTIMATION
    # =========================
    def _count_tokens(self, text: str) -> int:

        if self.tokenizer:
            return len(self.tokenizer.encode(text))

        # fallback approximation
        return len(text) // 4

    # =========================
    # TOKEN ESTIMATE
    # =========================
    def _estimate_tokens(self, chunks: List[ContextChunk]) -> int:

        return sum(self._count_tokens(c.text) for c in chunks)

    # =========================
    # SYSTEM PROMPT (STATIC)
    # =========================
    def _build_system_prompt(self) -> str:

        return (
            "You are a reasoning system. "
            "Use provided context only. "
            "Do not assume missing information."
        )