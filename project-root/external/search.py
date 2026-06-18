from __future__ import annotations

import asyncio
import logging
import unicodedata

import httpx
from app.settings import settings
from retrieval.query_preprocessor import extract_query_profile, geo_relevance_score

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

# ─── QUERY NORMALIZATION ──────────────────────────────────────────────────────

def _compose_search_query(query: str, lang: str) -> str:
    """
    Keep the original query intact, but add stable location aliases when the
    query is geo-sensitive. This helps providers converge on the right city
    without biasing toward any single language.
    """
    profile = extract_query_profile(query, lang)
    if not profile.is_geo_query or not profile.location:
        return query.strip()

    parts = [query.strip()]
    for variant in profile.aliases:
        if variant and variant.casefold() not in query.casefold():
            parts.append(variant)

    composed = " ".join(part for part in parts if part)
    return composed.strip()

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

def _filter_results(results: list[dict], query: str = "", lang: str = "en") -> list[dict]:
    """Sanitize URLs then delegate trust + geo filtering to source_credibility."""
    sanitized = [
        {**r, "link": _sanitize_url(r.get("link", ""))}
        for r in results
    ]
    return _credibility.filter_results(sanitized, max_results=5, query=query, lang=lang)


def _result_quality(results: list[dict], query: str, lang: str, query_kind: str) -> float:
    if not results:
        return 0.0
    best = 0.0
    for r in results:
        text = " ".join(str(r.get(k, "")) for k in ("title", "snippet", "address", "location"))
        geo = geo_relevance_score(query, text, lang=lang)
        keyword = 0.0
        qf = query.casefold()
        tf = text.casefold()
        if qf and tf:
            if qf in tf or tf in qf:
                keyword = 1.0
            else:
                q_tokens = {tok for tok in qf.split() if len(tok) > 2}
                t_tokens = {tok for tok in tf.split() if len(tok) > 2}
                if q_tokens and t_tokens:
                    keyword = len(q_tokens & t_tokens) / max(1, len(q_tokens | t_tokens))
        score = max(geo, keyword)
        best = max(best, score)
    if query_kind == "discovery":
        return round(best, 3)
    if query_kind == "advice":
        return round(max(best, 0.25 if results else 0.0), 3)
    if query_kind in {"hotel", "travel"}:
        return round(max(best, 0.35 if results else 0.0), 3)
    return round(best, 3)


# ─── VALIDATION ──────────────────────────────────────────────────────────────

_SUSPICIOUS_PATTERNS = {"негород", "negород", "dubrava_fake"}

def _validate_results(results: list[dict], query: str = "", lang: str = "en") -> list[dict]:
    if not results or not results[0].get("_structured"):
        return results

    profile = extract_query_profile(query, lang) if query else None
    validated = []
    for r in results:
        title = r.get("title", "").lower()
        if any(pat in title for pat in _SUSPICIOUS_PATTERNS):
            logger.warning("Validation: removed suspicious result", extra={"title": r.get("title")})
            continue
        if not r.get("title", "").strip():
            continue
        if profile and profile.is_geo_query and profile.location:
            affinity = geo_relevance_score(query, " ".join([
                r.get("title", ""), r.get("address", ""), r.get("snippet", "")
            ]), lang=lang)
            if affinity < 0.50:
                logger.debug(
                    "Validation: removed location mismatch",
                    extra={"title": r.get("title"), "affinity": round(affinity, 3), "location": profile.location},
                )
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
            filtered = _filter_results(results, query=query, lang=lang)
            quality = _result_quality(filtered, query=query, lang=lang, query_kind=extract_query_profile(query, lang).query_kind)
            if filtered and extract_query_profile(query, lang).query_kind == "discovery" and quality < 0.42:
                logger.info("Tavily results too weak for discovery query", extra={"quality": quality, "query": query[:50]})
                return []
            logger.info("Tavily search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
                "quality": quality,
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
                    validated = _validate_results(structured, query=query, lang=lang)
                    logger.info("SerpAPI hotel pack", extra={
                        "query": query[:50], "attempt": attempt + 1,
                        "hotels": len(validated), "lang": lang,
                    })
                    if validated:
                        quality = _result_quality(validated, query=query, lang=lang, query_kind=extract_query_profile(query, lang).query_kind)
                        if extract_query_profile(query, lang).query_kind == "discovery" and quality < 0.42:
                            logger.info("SerpAPI hotel pack too weak for discovery query", extra={"quality": quality, "query": query[:50]})
                            return []
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
            filtered = _filter_results(results, query=query, lang=lang)
            quality = _result_quality(filtered, query=query, lang=lang, query_kind=extract_query_profile(query, lang).query_kind)
            if filtered and extract_query_profile(query, lang).query_kind == "discovery" and quality < 0.42:
                logger.info("SerpAPI results too weak for discovery query", extra={"quality": quality, "query": query[:50]})
                return []
            logger.info("SerpAPI search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
                "quality": quality,
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
            _hf_token = getattr(settings, "hf_token", "")
            _headers = {"Authorization": f"Bearer {_hf_token}"} if _hf_token else {}
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(url, params=params, headers=_headers)
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
            filtered = _filter_results(results, query=query, lang=lang)
            quality = _result_quality(filtered, query=query, lang=lang, query_kind=extract_query_profile(query, lang).query_kind)
            if filtered and extract_query_profile(query, lang).query_kind == "discovery" and quality < 0.42:
                logger.info("SearXNG results too weak for discovery query", extra={"quality": quality, "query": query[:50]})
                return []
            logger.info("SearXNG search completed", extra={
                "query": query[:50], "attempt": attempt + 1,
                "raw": len(results), "filtered": len(filtered), "lang": lang,
                "quality": quality,
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
        query_for_search = _compose_search_query(query, lang)

        # 1. Tavily primary
        results = await _search_tavily(query_for_search, lang, num)
        if results is not None:
            return results

        # 2. SerpAPI secondary
        results = await _search_serpapi(query_for_search, lang, num)
        if results is not None:
            return results

        # 3. SearXNG tertiary
        return await _search_searxng(query_for_search, lang, num)

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        """
        Format search results into LLM-ready plain text.
        Pure function. No I/O.

        Returns "" when results is empty — NOT a localised placeholder.
        Reason: empty string → truth gate fires cleanly with no_grounded_data.
        """
        if not results:
            return ""

        header = "SEARCH RESULTS"

        # Structured hotel pack — deterministic formatter (SerpAPI-specific)
        if results[0].get("_structured"):
            lines: list[str] = [header]
            for i, r in enumerate(results, 1):
                entry = [f"{i}. {r.get('title', '')}"]
                if r.get("address"):
                    entry.append(f"   ADDRESS: {r['address']}")
                if r.get("rating"):
                    entry.append(f"   RATING: {r['rating']}")
                if r.get("price"):
                    entry.append(f"   PRICE: {r['price']}")
                if r.get("link"):
                    entry.append(f"   SOURCE: {r['link']}")
                lines.append("\n".join(entry))
            lines.append("Check official booking sites for live prices.")
            return "\n\n".join(lines)

        # Standard organic results
        lines = [header]
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. {r.get('title', '')}\n"
                f"   SNIPPET: {r.get('snippet', '')}\n"
                f"   SOURCE: {r.get('link', '')}"
            )
        return "\n\n".join(lines)


# Singleton
search_service = SearchService()