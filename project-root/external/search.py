import logging
from urllib.parse import urlparse

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://serpapi.com/search"
_TIMEOUT = 15.0

# SerpAPI supports hl (language) parameter
_SERP_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh-cn", "ja": "ja", "ko": "ko",
    "pl": "pl", "uk": "uk", "fa": "fa", "nl": "nl",
    "sv": "sv", "no": "no", "da": "da", "fi": "fi",
    "he": "iw", "vi": "vi", "th": "th", "id": "id",
    "ms": "ms", "hi": "hi", "bn": "bn", "ur": "ur",
    "az": "az", "kk": "kk", "uz": "uz", "ka": "ka",
    "hy": "hy", "mn": "mn", "sw": "sw", "am": "am",
    "cs": "cs", "sk": "sk", "ro": "ro", "hu": "hu",
    "bg": "bg", "hr": "hr", "sr": "sr",
    # Extended — fallback to English for SerpAPI
    "ha": "en", "yo": "en", "ig": "en", "so": "so",
    "ku": "en", "ps": "en", "ug": "en", "tt": "en",
}

# ─── SEO JUNK DOMAIN FILTER ───────────────────────────────────────────────────
# Domains that consistently return low-quality SEO aggregator content.
# These appear in search results but provide no useful grounded data —
# the LLM sees them and includes them in responses, causing bad outputs.
# Add domains here as new junk sources are discovered in production.
_JUNK_DOMAINS: frozenset[str] = frozenset({
    # Route/transport SEO aggregators
    "all-routes.ru",
    "all-routes.com",
    # Hotel SEO aggregators (use booking.com / hotels.com instead)
    "101hotels.com",
    # General Russian Q&A spam
    "otvet.mail.ru",
    "travelask.ru",
    # Generic travel SEO farms
    "tourister.ru",
    "turpravda.com",
    "votpusk.ru",
    # Map/route spam
    "mapbbcode.org",
    "kartagoroda.ru",
})


def _is_junk_domain(url: str) -> bool:
    """Return True if the URL's domain is in the junk list."""
    try:
        netloc = urlparse(url).netloc.lower()
        # Strip www. prefix
        domain = netloc[4:] if netloc.startswith("www.") else netloc
        return domain in _JUNK_DOMAINS
    except Exception:
        return False


def _filter_results(results: list[dict]) -> list[dict]:
    """
    Remove SEO junk domains and cap at 5 results sent to LLM.
    Fewer, higher-quality sources produce better synthesised answers.
    """
    filtered = [r for r in results if not _is_junk_domain(r.get("link", ""))]
    kept = filtered[:5]

    removed = len(results) - len(kept)
    if removed > 0:
        logger.info(
            "Search filter: removed junk/excess results",
            extra={"original": len(results), "kept": len(kept), "removed": removed},
        )
    return kept


class SearchService:
    """
    SerpAPI web search client.
    Read-only. No state. No interpretation.
    Returns filtered results — caller formats them.
    """

    def __init__(self) -> None:
        self._api_key = settings.serpapi_key

    async def search(
        self,
        query: str,
        lang: str = "en",
        num: int = 8,  # Fetch more than we need so filter has headroom
    ) -> list[dict]:
        """
        Perform web search.
        Returns list of filtered organic result dicts with keys:
        title, link, snippet.
        """
        if not self._api_key:
            logger.warning("SerpAPI key not set")
            return []

        params = {
            "q": query,
            "api_key": self._api_key,
            "engine": "google",
            "hl": _SERP_LANG_MAP.get(lang, "en"),
            "num": num,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                raw_results = data.get("organic_results", [])

                results = [
                    {
                        "title":   r.get("title", ""),
                        "link":    r.get("link", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    for r in raw_results
                ]

                # Filter junk domains before returning
                filtered = _filter_results(results)

                logger.info("Search completed", extra={
                    "query":    query[:50],
                    "raw":      len(results),
                    "filtered": len(filtered),
                    "lang":     lang,
                })
                return filtered

        except Exception as exc:
            logger.error("SearchService.search failed", extra={
                "query": query[:50],
                "error": str(exc),
            })
            return []

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        """
        Format search results into Telegram-ready text.
        Pure function. No I/O.
        """
        if not results:
            from i18n.t import t as _t
            return _t("no_search_results", lang)

        lines: list[str] = []
        for i, r in enumerate(results, 1):
            title   = r.get("title", "")
            link    = r.get("link", "")
            snippet = r.get("snippet", "")
            lines.append(f"{i}. {title}\n{snippet}\nSource: {link}")

        return "\n\n".join(lines)


# Singleton
search_service = SearchService()