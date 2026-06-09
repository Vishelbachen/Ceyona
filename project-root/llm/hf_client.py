"""HuggingFace Inference client with BGE model constants.

Single module-level client instance (hf_client) shared across the codebase.
Exposes:
  - BGE_LARGE, BGE_SMALL, BGE_RERANKER  — canonical model name constants
  - hf_client                            — singleton with embed() and rerank()
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# ─── Model name constants ────────────────────────────────────────────────────
BGE_LARGE = "BAAI/bge-large-en-v1.5"
BGE_SMALL = "BAAI/bge-small-en-v1.5"
BGE_RERANKER = "BAAI/bge-reranker-large"


# ─── Client ──────────────────────────────────────────────────────────────────

class _HFClient:
    """Async HuggingFace Inference client.

    Wraps huggingface_hub.AsyncInferenceClient.  The token is read once at
    import time from the HF_TOKEN env variable; in production it is injected
    by the app settings layer before any module-level code runs.
    """

    def __init__(self) -> None:
        token = os.getenv("HF_TOKEN", "")
        try:
            from huggingface_hub import AsyncInferenceClient  # type: ignore
            self._client = AsyncInferenceClient(token=token or None)
        except ImportError:
            logger.warning("huggingface_hub not installed — hf_client is a stub")
            self._client = None

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def embed(
        self,
        texts: list[str],
        model: str = BGE_LARGE,
    ) -> list[list[float]]:
        """Return embedding vectors for *texts* using *model*.

        Returns a list of float vectors in the same order as *texts*.
        On error returns an empty list so callers can treat it as a cache miss.
        """
        if not texts:
            return []
        if self._client is None:
            logger.error("hf_client stub: embed() called but huggingface_hub is missing")
            return []
        try:
            result = await self._client.feature_extraction(texts, model=model)
            # huggingface_hub returns a nested list or numpy array
            if hasattr(result, "tolist"):
                result = result.tolist()
            # Ensure shape is list[list[float]]
            if result and not isinstance(result[0], list):
                result = [result]
            return result  # type: ignore[return-value]
        except Exception as exc:
            logger.error("hf_client.embed failed", extra={"model": model, "error": str(exc)})
            return []

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        candidates: list[str],
        model: str = BGE_RERANKER,
    ) -> list[float]:
        """Score *candidates* against *query* using a cross-encoder *model*.

        Returns a list of float scores in the same order as *candidates*.
        On error returns a list of zeros so the caller can fall back gracefully.
        """
        if not candidates:
            return []
        if self._client is None:
            logger.error("hf_client stub: rerank() called but huggingface_hub is missing")
            return [0.0] * len(candidates)
        try:
            pairs = [{"text": query, "text_pair": c} for c in candidates]
            result = await self._client.text_classification(pairs, model=model)
            # Returns list[ClassificationOutput]; extract the score of the first label.
            scores: list[float] = []
            for item in result:
                if isinstance(item, list):
                    scores.append(float(item[0].score) if item else 0.0)
                elif hasattr(item, "score"):
                    scores.append(float(item.score))
                else:
                    scores.append(0.0)
            return scores
        except Exception as exc:
            logger.error("hf_client.rerank failed", extra={"model": model, "error": str(exc)})
            return [0.0] * len(candidates)


# Module-level singleton — imported as `from llm.hf_client import hf_client`
hf_client = _HFClient()
