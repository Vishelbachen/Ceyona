import logging

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

# ─── SOURCE CREDIBILITY ───────────────────────────────────────────────────────
# Domain trust evaluation is delegated to retrieval/source_credibility.py.
# That module is the single source of truth for domain trust classification.
# Do NOT add junk domains here — add them to retrieval/source_credibility.py.
from retrieval.source_credibility import source_credibility as _credibility


def _sanitize_url(url: str) -> str:
    """
    Normalize URLs that contain lookalike or subscript Unicode characters.
    Example: hotel.tutu.ru/c\u1d63ussia → hotel.tutu.ru/crussia
    SerpAPI occasionally returns URLs with Unicode variants of ASCII letters
    (subscript, superscript, fullwidth). These break as clickable links in
    Telegram and confuse the LLM when it tries to cite them.
    """
    if not url:
        return url
    # Unicode ranges that are lookalike ASCII letters in URLs:
    # U+1D00–U+1DBF  Phonetic Extensions (subscript/superscript letters)
    # U+FF01–U+FF5E  Fullwidth ASCII variants
    # U+2070–U+209F  Superscript digits
    import unicodedata
    sanitized = []
    for ch in url:
        cp = ord(ch)
        # Fullwidth ASCII: U+FF01–U+FF5E → subtract 0xFEE0 to get ASCII
        if 0xFF01 <= cp <= 0xFF5E:
            sanitized.append(chr(cp - 0xFEE0))
        # Subscript/superscript phonetic: map to plain ASCII where possible
        elif 0x1D00 <= cp <= 0x1DBF:
            # Decompose to closest ASCII equivalent via NFKD
            decomposed = unicodedata.normalize("NFKD", ch)
            sanitized.append(decomposed if decomposed.isascii() else ch)
        else:
            sanitized.append(ch)
    return "".join(sanitized)


def _filter_results(results: list[dict]) -> list[dict]:
    """
    Sanitize URLs then delegate trust filtering to source_credibility.
    source_credibility is the single source of truth for domain quality.
    """
    sanitized = [
        {**r, "link": _sanitize_url(r.get("link", ""))}
        for r in results
    ]
    return _credibility.filter_results(sanitized, max_results=3)


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
        num: int = 6,  # Fetch slightly more than we need so filter has headroom
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

        Returns "" when results is empty — NOT a localised placeholder string.
        Reason: a non-empty placeholder fools the STRICT truth gate into thinking
        the tool returned real data, so LLM gets a useless context and synthesizer
        produces a generic error. Empty string → _run_tool returns None →
        truth gate fires cleanly with no_grounded_data message.
        """
        if not results:
            return ""

        lines: list[str] = []
        for i, r in enumerate(results, 1):
            title   = r.get("title", "")
            link    = r.get("link", "")
            snippet = r.get("snippet", "")
            lines.append(f"{i}. {title}\n{snippet}\nSource: {link}")

        return "\n\n".join(lines)


# Singleton
search_service = SearchService()