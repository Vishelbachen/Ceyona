import logging
import httpx
from app.settings import settings

logger = logging.getLogger(__name__)
_BASE = "https://serpapi.com/search"
_TIMEOUT = 15.0


async def web_search(query: str, num: int = 5) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(_BASE, params={
                "q": query,
                "api_key": settings.serpapi_key,
                "num": num,
                "engine": "google",
            })
            r.raise_for_status()
            results = r.json().get("organic_results", [])
            return [
                {
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                }
                for item in results[:num]
            ]
    except Exception as exc:
        logger.error("Web search failed", extra={"query": query, "error": str(exc)})
        return []