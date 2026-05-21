import asyncio
import logging

import httpx
from app.settings import settings

logger = logging.getLogger(__name__)

# HuggingFace migrated Inference API to the new router in 2024.
# Old endpoint (returns 404): https://api-inference.huggingface.co/models/{model}
# New endpoint:               https://router.huggingface.co/hf-inference/models/{model}
_BASE_URL = "https://router.huggingface.co/hf-inference/models"

# Increased from 30s to 60s — free HF Inference API cold starts can take 40-50s.
_TIMEOUT = 60.0

# Retry config for cold-start / transient failures.
_MAX_RETRIES = 3
_RETRY_DELAY = 5.0  # seconds between retries

_HEADERS = {
    "Authorization": f"Bearer {settings.hf_token}",
    "Content-Type": "application/json",
}

# ─── MODEL IDENTIFIERS ───────────────────────────────────────────────────────

BGE_LARGE    = "BAAI/bge-large-en-v1.5"
BGE_SMALL    = "BAAI/bge-small-en-v1.5"
BGE_RERANKER = "BAAI/bge-reranker-large"


class HFClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )

    async def _post_with_retry(self, path: str, payload: dict) -> object:
        """
        POST with retry on timeout or 503 (model loading).
        Free HF Inference API cold starts can exceed 30s on first request.
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._http.post(path, json=payload)
                # 503 means model is loading — retry after delay
                if response.status_code == 503:
                    estimated = response.json().get("estimated_time", _RETRY_DELAY)
                    wait = min(float(estimated), 30.0)
                    logger.warning(
                        "HF model loading, retrying",
                        extra={"attempt": attempt, "wait": wait, "path": path},
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_exc = exc
                logger.warning(
                    "HF timeout, retrying",
                    extra={"attempt": attempt, "max": _MAX_RETRIES, "path": path},
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY)
            except Exception as exc:
                logger.error(
                    "HF request failed",
                    extra={"attempt": attempt, "error": str(exc), "path": path},
                )
                raise

        raise last_exc or RuntimeError(f"HF request failed after {_MAX_RETRIES} retries")

    async def embed(
        self,
        texts: list[str],
        model: str = BGE_LARGE,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Returns list of float vectors.
        """
        data = await self._post_with_retry(
            f"/{model}",
            {"inputs": texts, "options": {"wait_for_model": True}},
        )
        return data  # type: ignore[return-value]

    async def rerank(
        self,
        query: str,
        candidates: list[str],
        model: str = BGE_RERANKER,
    ) -> list[float]:
        """
        Rerank candidates against a query.
        Returns list of relevance scores (same order as candidates).
        """
        pairs = [[query, candidate] for candidate in candidates]
        data = await self._post_with_retry(
            f"/{model}",
            {"inputs": pairs, "options": {"wait_for_model": True}},
        )

        # HF reranker returns list of [{"score": float}]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return [item["score"] for item in data]  # type: ignore[index]

        return data  # type: ignore[return-value]

    async def aclose(self) -> None:
        await self._http.aclose()


# Singleton
hf_client = HFClient()
