from __future__ import annotations

import asyncio
import logging
import unicodedata
from urllib.parse import urlparse

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://serpapi.com/search"
_TIMEOUT  = 20.0   # raised from 15s — SerpAPI can be slow under load
_RETRIES  = 2      # total attempts = 1 + _RETRIES
_RETRY_DELAYS = (1.0, 2.0)   # seconds between retries (exponential)

# SerpAPI hl (interface language) parameter map
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
    # Extended — SerpAPI falls back to English for unsupported langs
    "ha": "en", "yo": "en", "ig": "en", "so": "so",
    "ku": "en", "ps": "en", "ug": "en", "tt": "en",
}


# ─── SOURCE CREDIBILITY ───────────────────────────────────────────────────────
# Domain trust evaluation is delegated to retrieval/source_credibility.py.
# That module is the single source of truth for domain trust classification.
from retrieval.source_credibility import source_credibility as _credibility


# ─── URL SANITIZATION ─────────────────────────────────────────────────────────

def _sanitize_url(url: str) -> str:
    """
    Normalize URLs containing lookalike/subscript Unicode characters.
    SerpAPI occasionally returns URLs with U+1D63 (subscript r) and similar
    characters that break clickable links in Telegram.

    Examples:
      hotel.tutu.ru/c\u1d63ussia → hotel.tutu.ru/crussia
    """
    if not url:
        return url
    sanitized = []
    for ch in url:
        cp = ord(ch)
        # Fullwidth ASCII U+FF01–U+FF5E → subtract 0xFEE0 to get ASCII
        if 0xFF01 <= cp <= 0xFF5E:
            sanitized.append(chr(cp - 0xFEE0))
        # Phonetic extensions U+1D00–U+1DBF → NFKD to ASCII equivalent
        elif 0x1D00 <= cp <= 0x1DBF:
            decomposed = unicodedata.normalize("NFKD", ch)
            sanitized.append(decomposed if decomposed.isascii() else ch)
        else:
            sanitized.append(ch)
    return "".join(sanitized)


# ─── FILTER ───────────────────────────────────────────────────────────────────

def _filter_results(results: list[dict]) -> list[dict]:
    """
    Sanitize URLs then delegate trust filtering to source_credibility.
    source_credibility is the single source of truth for domain quality.
    """
    sanitized = [
        {**r, "link": _sanitize_url(r.get("link", ""))}
        for r in results
    ]
    return _credibility.filter_results(sanitized, max_results=5)


# ─── VALIDATION ──────────────────────────────────────────────────────────────

# Patterns that indicate fabricated/suspicious hotel names
# These appear in LLM hallucinations but not in real SerpAPI results
_SUSPICIOUS_PATTERNS = {
    "негород", "negород", "dubrava_fake",
}

def _validate_results(results: list[dict]) -> list[dict]:
    """
    Post-filter validation: remove results that look fabricated.
    Only applied to structured hotel results where name verification matters.
    For organic results: trust source_credibility filter.
    """
    if not results or not results[0].get("_structured"):
        return results

    validated = []
    for r in results:
        title = r.get("title", "").lower()
        # Remove if matches known hallucination patterns
        if any(pat in title for pat in _SUSPICIOUS_PATTERNS):
            logger.warning("Validation: removed suspicious result", extra={"title": r.get("title")})
            continue
        # Remove if no name at all
        if not r.get("title", "").strip():
            continue
        validated.append(r)

    return validated


# ─── SERVICE ──────────────────────────────────────────────────────────────────

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
        num: int = 10,
    ) -> list[dict]:
        """
        Perform web search with retry.
        For hotel/accommodation queries: also extracts structured hotels_results
        from SerpAPI (price, rating, address) when available.

        Returns list of filtered result dicts:
          [{"title": str, "link": str, "snippet": str,
            "price": str, "rating": str, "address": str}]  ← extras when available

        Returns [] on all failures.
        """
        if not self._api_key:
            logger.warning("SerpAPI key not set")
            return []

        params = {
            "q":       query,
            "api_key": self._api_key,
            "engine":  "google",
            "hl":      _SERP_LANG_MAP.get(lang, "en"),
            "num":     num,
        }

        last_exc: Exception | None = None

        for attempt in range(1 + _RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.get(_BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()

                    # ── structured hotels_results (when Google returns hotel pack) ──
                    hotel_pack = data.get("hotels_results", {})
                    hotel_properties = hotel_pack.get("properties", [])
                    if hotel_properties:
                        structured: list[dict] = []
                        for h in hotel_properties[:8]:
                            name    = h.get("name", "")
                            price   = h.get("rate_per_night", {}).get("lowest", "") or h.get("price", "")
                            rating  = str(h.get("overall_rating", "")) or str(h.get("rating", ""))
                            address = h.get("address", "") or h.get("location", "")
                            link    = h.get("link", "") or h.get("serpapi_property_link", "")
                            snippet = h.get("description", "") or h.get("snippet", "")
                            if name:
                                structured.append({
                                    "title":   name,
                                    "link":    _sanitize_url(link),
                                    "snippet": snippet,
                                    "price":   str(price),
                                    "rating":  rating,
                                    "address": address,
                                    "_structured": True,
                                })
                        if structured:
                            validated = _validate_results(structured)
                            logger.info("Search completed (hotel pack)", extra={
                                "query":    query[:50],
                                "attempt":  attempt + 1,
                                "hotels":   len(validated),
                                "lang":     lang,
                            })
                            if validated:
                                return validated

                    # ── fallback: organic results ──────────────────────────────
                    raw_results = data.get("organic_results", [])
                    results = [
                        {
                            "title":   r.get("title", ""),
                            "link":    _sanitize_url(r.get("link", "")),
                            "snippet": r.get("snippet", ""),
                        }
                        for r in raw_results
                    ]
                    filtered = _filter_results(results)
                    logger.info("Search completed", extra={
                        "query":    query[:50],
                        "attempt":  attempt + 1,
                        "raw":      len(results),
                        "filtered": len(filtered),
                        "lang":     lang,
                    })
                    return filtered

            except Exception as exc:
                last_exc = exc
                logger.warning("SearchService.search attempt failed", extra={
                    "query":   query[:50],
                    "attempt": attempt + 1,
                    "error":   str(exc),
                })
                if attempt < _RETRIES:
                    delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                    await asyncio.sleep(delay)

        logger.error("SearchService.search failed after all retries", extra={
            "query": query[:50],
            "error": str(last_exc),
        })
        return []

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        """
        Format search results into LLM-ready plain text.
        Pure function. No I/O.

        Returns "" when results is empty — NOT a localised placeholder.
        Reason: a non-empty placeholder fools the STRICT truth gate into
        thinking the tool returned real data → LLM gets useless context →
        synthesizer produces generic error. Empty string → truth gate fires
        cleanly with no_grounded_data message.

        Structured hotel results (from hotels_results pack) are formatted
        with explicit price/rating/address fields so the LLM has no reason
        to invent them.
        """
        if not results:
            return ""

        # Structured hotel pack — use rich formatter
        if results[0].get("_structured"):
            lines: list[str] = []
            for i, r in enumerate(results, 1):
                name    = r.get("title", "")
                price   = r.get("price", "")
                rating  = r.get("rating", "")
                address = r.get("address", "")
                link    = r.get("link", "")
                snippet = r.get("snippet", "")

                entry = f"[{i}] {name}"
                if rating:
                    entry += f"\nРейтинг: {rating}"
                if price:
                    entry += f"\nЦена: {price}"
                if address:
                    entry += f"\nАдрес: {address}"
                if snippet:
                    entry += f"\n{snippet}"
                if link:
                    entry += f"\nСсылка: {link}"
                lines.append(entry)

            header = "=== ДАННЫЕ ИЗ ПОИСКА (используй ТОЛЬКО эти факты) ===\n"
            return header + "\n\n".join(lines)

        # Standard organic results
        lines = []
        for i, r in enumerate(results, 1):
            title   = r.get("title", "")
            link    = r.get("link", "")
            snippet = r.get("snippet", "")
            lines.append(f"[{i}] {title}\n{snippet}\nИсточник: {link}")

        header = "=== ДАННЫЕ ИЗ ПОИСКА (используй ТОЛЬКО эти факты) ===\n"
        return header + "\n\n".join(lines)


# Singleton
search_service = SearchService()