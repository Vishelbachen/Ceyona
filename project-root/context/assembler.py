from typing import Any, Dict, List, Optional


class ContextAssembler:
    """
    AI Platform v4.7 — Context Assembler

    RESPONSIBILITY:
    - Convert ranked retrieval results into LLM-ready context
    - Preserve ordering from reranker
    - Format data into structured prompt segments

    STRICT RULES:
    - No semantic filtering
    - No summarization logic
    - No LLM / memory / retrieval reasoning
    - No re-ranking or scoring changes
    - No orchestration decisions
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation (1 token ≈ 4 chars).
        """

        return len(text) // 4

    def assemble(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds final context payload for LLM.
        """

        context_blocks = []
        total_tokens = 0

        for doc in documents:
            content = doc.get("content", "")
            tokens = self._estimate_tokens(content)

            if total_tokens + tokens > self.max_tokens:
                break

            context_blocks.append({
                "id": doc.get("id"),
                "source": doc.get("source"),
                "content": content,
                "score": doc.get("rerank_score", doc.get("score", 0.0)),
            })

            total_tokens += tokens

        return {
            "query": query,
            "context": context_blocks,
            "token_estimate": total_tokens,
        }