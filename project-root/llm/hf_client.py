import httpx

from app.settings import settings

# HuggingFace migrated Inference API to the new router in 2024.
# Old endpoint (returns 404): https://api-inference.huggingface.co/models/{model}
# New endpoint:               https://router.huggingface.co/hf-inference/models/{model}
_BASE_URL = "https://router.huggingface.co/hf-inference/models"
_TIMEOUT = 30.0

_HEADERS = {
    "Authorization": f"Bearer {settings.hf_token}",
    "Content-Type": "application/json",
}

# ─── MODEL IDENTIFIERS ───────────────────────────────────────────────────────

BGE_LARGE = "BAAI/bge-large-en-v1.5"
BGE_SMALL = "BAAI/bge-small-en-v1.5"
BGE_RERANKER = "BAAI/bge-reranker-large"


class HFClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )

    async def embed(
        self,
        texts: list[str],
        model: str = BGE_LARGE,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Returns list of float vectors.
        """
        response = await self._http.post(
            f"/{model}",
            json={"inputs": texts, "options": {"wait_for_model": True}},
        )
        response.raise_for_status()
        return response.json()

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
        response = await self._http.post(
            f"/{model}",
            json={"inputs": pairs, "options": {"wait_for_model": True}},
        )
        response.raise_for_status()
        data = response.json()

        # HF reranker returns list of [{"score": float}]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return [item["score"] for item in data]

        return data

    async def aclose(self) -> None:
        await self._http.aclose()


# Singleton
hf_client = HFClient()