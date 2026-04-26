from __future__ import annotations

import aiohttp
from typing import Dict, Any, List, Optional

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# SEARCH CLIENT
# =========================
class SearchClient:
    """
    ROLE:
    - execute external web search queries (SERPAPI or similar)
    - return raw ranked results
    - normalize structure for retrieval/context layer

    STRICT RULES:
    - no summarization
    - no ranking modification
    - no semantic interpretation
    - no answer generation
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY

    # =========================
    # SEARCH
    # =========================
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:

        params = {
            "q": query,
            "api_key": self.api_key,
            "num": limit,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                data = await resp.json()

        return self._normalize(data)

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:

        organic = data.get("organic_results", [])

        return {
            "results": [
                {
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": item.get("source"),
                }
                for item in organic
            ],
            "raw": data,
        }