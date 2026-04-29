import logging
import httpx

logger = logging.getLogger(__name__)
_TIMEOUT = 15.0
_MAX_CHARS = 5000


async def fetch_page(url: str) -> str:
    """Fetch raw text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text[:_MAX_CHARS]
    except Exception as exc:
        logger.error("Page fetch failed", extra={"url": url, "error": str(exc)})
        return ""