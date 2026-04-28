from typing import Any, Dict, List, Optional


class SearchClient:
    """
    AI Platform v4.7 — External Search Client

    RESPONSIBILITY:
    - Execute web search queries via external provider (e.g. SerpAPI)
    - Return raw search results
    - Provide unprocessed SERP data to retrieval layer

    STRICT RULES:
    - No ranking or reranking logic
    - No summarization
    - No semantic interpretation
    - No LLM / memory / retrieval usage
    - No decision-making
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://serpapi.com"

    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Executes a raw web search request.
        """

        return {
            "query": query,
            "results": [
                {
                    "title": "mock result",
                    "url": "https://example.com",
                    "snippet": "mock snippet",
                }
                for _ in range(num_results)
            ],
            "source": "mock_serpapi",
        }

    async def news_search(
        self,
        query: str,
        num_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Executes a news-specific search.
        """

        return {
            "query": query,
            "results": [
                {
                    "title": "mock news",
                    "url": "https://news.example.com",
                    "snippet": "mock news snippet",
                    "published_at": "2026-01-01",
                }
                for _ in range(num_results)
            ],
            "source": "mock_serpapi_news",
        }

    async def image_search(
        self,
        query: str,
        num_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes image search.
        """

        return {
            "query": query,
            "images": [
                {
                    "url": "https://example.com/image.jpg",
                    "thumbnail": "https://example.com/thumb.jpg",
                }
                for _ in range(num_results)
            ],
            "source": "mock_serpapi_images",
        }