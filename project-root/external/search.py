from __future__ import annotations

import asyncio
import logging
import unicodedata

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

# ─── PROVIDER CONFIG ──────────────────────────────────────────────────────────
#
# Three-tier fallback chain (architecture §search, audit §13.5):
#
#   1. Tavily   (primary)   — LLM-optimised, structured content, 1000 req/mo free
#   2. SerpAPI  (secondary) — reliable reserve, 250 req/mo free, hotel pack support
#   3. SearXNG  (tertiary)  — meta-search, no limit, self-hosted or public, unstable
#
# Each provider is tried in order. First success wins.
# Provider is skipped silently if its key/URL is not configured.

_TAVILY_URL  = "https://api.tavily.com/search"
_SERPAPI_URL = "https://serpapi.com/search"
_TIMEOUT     = 20.0
_RETRIES     = 2
_RETRY_DELAYS = (1.0, 2.0)

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
    "ha": "en", "yo": "en", "ig": "en", "so": "so",
    "ku": "en", "ps": "en", "ug": "en", "tt": "en",
}


# ─── SOURCE CREDIBILITY ───────────────────────────────────────────────────────
from retrieval.source_credibility import source_credibility as _credibility

# ─── URL SANITIZATION ─────────────────────────────────────────────────────────

def _sanitize_url(url: str) -> str:
    """
    Normalize URLs containing lookalike/subscript Unicode characters.
    SerpAPI occasionally returns URLs with U+1D63 (subscript r) and similar
    characters that break clickable links in Telegram.
    """
    if not url:
        return url
    sanitized = []
    for ch in url:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            sanitized.append(chr(cp - 0xFEE0))
        elif 0x1D00 <= cp <= 0x1DBF:
            decomposed = unicodedata.normalize("NFKD", ch)
            sanitized.append(decomposed if decomposed.isascii() else ch)
        else:
            sanitized.append(ch)
    return "".join(sanitized)


# ─── FILTER ───────────────────────────────────────────────────────────────────

def _filter_results(results: list[dict]) -> list[dict]:
    """Sanitize URLs then delegate trust filtering to source_credibility."""
    sanitized = [
        {**r, "link": _sanitize_url(r.get("link", ""))}
        for r in results
    ]
    return _credibility.filter_results(sanitized, max_results=5)


# ─── VALIDATION ──────────────────────────────────────────────────────────────

_SUSPICIOUS_PATTERNS = {"негород", "negород", "dubrava_fake"}

def _validate_results(results: list[dict]) -> list[dict]:
    if not results or not results[0].get("_structured"):
        return results
    validated = []
    for r in results:
        title = r.get("title", "").lower()
        if any(pat in title for pat in _SUSPICIOUS_PATTERNS):
            logger.warning("Validation: removed suspicious result", extra={"title": r.get("title")})
            continue
        if not r.get("title", "").strip():
            continue
        validated.append(r)
    return validated


# ─── PROVIDER 1: TAVILY ───────────────────────────────────────────────────────

async def _search_tavily(query: str, lang: str, num: int) -> list[dict] | None:
    """
    Primary provider. LLM-optimised structured results.
    Returns None on failure or if key not configured → triggers next provider.
    """
    api_key = settings.tavily_api_key
    if not api_key:
        return None

    payload = {
        "api_key":             api_key,
        "query":               query,
        "search_depth":        "basic",
        "include_answer":      False,
        "include_raw_content": False,
        "max_results":         num,
    }

    last_exc: Exception | None = None
    for attempt in range(1 + _RETRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(_TAVILY_URL, json=payload)
                response.raise_for_status()
                data = response.json()

            raw = data.get("results", [])
            results = [
                {
                    "title":   r.get("title", ""),
                    "link":    _sanitize_url(r.get("url", "")),
                    "snippet": r.get("content", ""),
                }
                for r in raw
                if r.get("title") or r.get("content")
            ]
            filtered = _filter_results(results)
            logger.info("Tavily search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
            })
            return filtered

        except Exception as exc:
            last_exc = exc
            logger.warning("Tavily attempt failed", extra={
                "query": query[:50], "attempt": attempt + 1, "error": str(exc),
            })
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("Tavily failed — falling back to SerpAPI", extra={
        "query": query[:50], "error": str(last_exc),
    })
    return None


# ─── PROVIDER 2: SERPAPI ──────────────────────────────────────────────────────

async def _search_serpapi(query: str, lang: str, num: int) -> list[dict] | None:
    """
    Secondary provider. Also handles Google hotel pack extraction.
    Returns None on failure or if key not configured → triggers SearXNG.
    """
    api_key = settings.serpapi_key
    if not api_key:
        return None

    params = {
        "q":       query,
        "api_key": api_key,
        "engine":  "google",
        "hl":      _SERP_LANG_MAP.get(lang, "en"),
        "num":     num,
    }

    last_exc: Exception | None = None
    for attempt in range(1 + _RETRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(_SERPAPI_URL, params=params)
                response.raise_for_status()
                data = response.json()

            # ── structured hotel pack (SerpAPI-specific) ──────────────────
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
                            "title": name, "link": _sanitize_url(link),
                            "snippet": snippet, "price": str(price),
                            "rating": rating, "address": address,
                            "_structured": True,
                        })
                if structured:
                    validated = _validate_results(structured)
                    logger.info("SerpAPI hotel pack", extra={
                        "query": query[:50], "attempt": attempt + 1,
                        "hotels": len(validated), "lang": lang,
                    })
                    if validated:
                        return validated

            # ── organic results ───────────────────────────────────────────
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
            logger.info("SerpAPI search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
            })
            return filtered

        except Exception as exc:
            last_exc = exc
            logger.warning("SerpAPI attempt failed", extra={
                "query": query[:50], "attempt": attempt + 1, "error": str(exc),
            })
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("SerpAPI failed — falling back to SearXNG", extra={
        "query": query[:50], "error": str(last_exc),
    })
    return None


# ─── PROVIDER 3: SEARXNG ──────────────────────────────────────────────────────

async def _search_searxng(query: str, lang: str, num: int) -> list[dict]:
    """
    Tertiary provider. Meta-search (Google, Bing, DuckDuckGo aggregated).
    No API key — requires SEARXNG_URL (self-hosted or public instance).
    Public instances are unstable — this is last-chance fallback only.
    Returns [] on failure or if URL not configured.
    """
    base_url = settings.searxng_url
    if not base_url:
        return []

    params = {
        "q":       query,
        "format":  "json",
        "language": lang,
        "pageno":  1,
    }

    last_exc: Exception | None = None
    for attempt in range(1 + _RETRIES):
        try:
            url = base_url.rstrip("/") + "/search"
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            raw = data.get("results", [])[:num]
            results = [
                {
                    "title":   r.get("title", ""),
                    "link":    _sanitize_url(r.get("url", "")),
                    "snippet": r.get("content", ""),
                }
                for r in raw
                if r.get("title") or r.get("content")
            ]
            filtered = _filter_results(results)
            logger.info("SearXNG search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
            })
            return filtered

        except Exception as exc:
            last_exc = exc
            logger.warning("SearXNG attempt failed", extra={
                "query": query[:50], "attempt": attempt + 1, "error": str(exc),
            })
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("SearXNG failed — all providers exhausted", extra={
        "query": query[:50], "error": str(last_exc),
    })
    return []


# ─── SERVICE ──────────────────────────────────────────────────────────────────

class SearchService:
    """
    Web search with three-tier provider fallback chain.

    Priority (architecture §search):
      1. Tavily   — primary, LLM-optimised, 1000 req/mo free
      2. SerpAPI  — secondary, reliable reserve, 250 req/mo free, hotel pack
      3. SearXNG  — tertiary, meta-search, no limit, last resort

    Each provider skipped silently if not configured.
    compound_agent calls search_service.search() — provider selection is invisible to caller.
    """

    async def search(
        self,
        query: str,
        lang: str = "en",
        num: int = 10,
    ) -> list[dict]:
        """
        Search with Tavily → SerpAPI → SearXNG fallback.

        Returns list of filtered result dicts:
          [{"title": str, "link": str, "snippet": str}]
          + hotel pack extras when SerpAPI returns structured results:
          {"price": str, "rating": str, "address": str, "_structured": True}

        Returns [] when all providers fail or are unconfigured.
        """
        # 1. Tavily primary
        results = await _search_tavily(query, lang, num)
        if results is not None:
            return results

        # 2. SerpAPI secondary
        results = await _search_serpapi(query, lang, num)
        if results is not None:
            return results

        # 3. SearXNG tertiary
        return await _search_searxng(query, lang, num)

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        """
        Format search results into LLM-ready plain text.
        Pure function. No I/O.

        Returns "" when results is empty — NOT a localised placeholder.
        Reason: empty string → truth gate fires cleanly with no_grounded_data.
        """
        if not results:
            return ""

        # Structured hotel pack — deterministic formatter (SerpAPI-specific)
        if results[0].get("_structured"):
            lines: list[str] = []
            for i, r in enumerate(results, 1):
                entry = f"{i}. {r.get('title', '')}"
                if r.get("address"):
                    entry += f"\n   📍 {r['address']}"
                if r.get("rating"):
                    entry += f"\n   ⭐ {r['rating']}"
                if r.get("price"):
                    entry += f"\n   💰 {r['price']}"
                if r.get("link"):
                    entry += f"\n   🔗 {r['link']}"
                lines.append(entry)
            header = "=== ДАННЫЕ ИЗ ПОИСКА ===\n"
            footer = "\n\nПроверьте актуальные цены на Booking.com или официальных сайтах."
            return header + "\n\n".join(lines) + footer

        # Standard organic results
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"[{i}] {r.get('title', '')}\n"
                f"{r.get('snippet', '')}\n"
                f"Источник: {r.get('link', '')}"
            )
        return "=== ДАННЫЕ ИЗ ПОИСКА ===\n" + "\n\n".join(lines)


# Singleton
search_service = SearchService()