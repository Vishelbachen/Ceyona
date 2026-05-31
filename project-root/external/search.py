from __future__ import annotations

import asyncio
import logging
import unicodedata

import httpx

from app.settings import settings
from contracts.retrieval_contracts import SearchOutcome, SearchStatus
from retrieval.query_preprocessor import extract_query_profile, geo_relevance_score
from retrieval.source_credibility import source_credibility as _credibility

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"
_SERPAPI_URL = "https://serpapi.com/search"
_TIMEOUT = 20.0
_RETRIES = 2
_RETRY_DELAYS = (1.0, 2.0)

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

_SUSPICIOUS_PATTERNS = {"негород", "negород", "dubrava_fake"}


def _compose_search_query(query: str, lang: str) -> str:
    profile = extract_query_profile(query, lang)
    if not profile.is_geo_query or not profile.location:
        return query.strip()

    parts = [query.strip()]
    for variant in profile.aliases:
        if variant and variant.casefold() not in query.casefold():
            parts.append(variant)
    return " ".join(part for part in parts if part).strip()


def _sanitize_url(url: str) -> str:
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


def _filter_results(results: list[dict], query: str = "", lang: str = "en") -> list[dict]:
    sanitized = [{**r, "link": _sanitize_url(r.get("link", ""))} for r in results]
    return _credibility.filter_results(sanitized, max_results=5, query=query, lang=lang)


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


def _make_outcome(
    provider: str,
    query: str,
    results: list[dict],
    *,
    status: SearchStatus = SearchStatus.SUCCESS,
    error: str = "",
) -> SearchOutcome:
    return SearchOutcome(results=results, status=status, provider=provider, error=error, query=query)


async def _search_tavily(query: str, lang: str, num: int) -> SearchOutcome:
    api_key = settings.tavily_api_key
    if not api_key:
        return _make_outcome("tavily", query, [], status=SearchStatus.CONFIG_MISSING)

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": num,
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
                {"title": r.get("title", ""), "link": _sanitize_url(r.get("url", "")), "snippet": r.get("content", "")}
                for r in raw
                if r.get("title") or r.get("content")
            ]
            filtered = _filter_results(results, query=query, lang=lang)
            logger.info("Tavily search completed", extra={"query": query[:50], "attempt": attempt + 1, "raw": len(results), "filtered": len(filtered), "lang": lang})
            if filtered:
                return _make_outcome("tavily", query, filtered)
            if results:
                return _make_outcome("tavily", query, [], status=SearchStatus.FILTERED_OUT)
            return _make_outcome("tavily", query, [], status=SearchStatus.NO_RESULTS)
        except Exception as exc:
            last_exc = exc
            logger.warning("Tavily attempt failed", extra={"query": query[:50], "attempt": attempt + 1, "error": str(exc)})
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("Tavily failed — falling back to SerpAPI", extra={"query": query[:50], "error": str(last_exc)})
    return _make_outcome("tavily", query, [], status=SearchStatus.PROVIDER_ERROR, error=str(last_exc) if last_exc else "")


async def _search_serpapi(query: str, lang: str, num: int) -> SearchOutcome:
    api_key = settings.serpapi_key
    if not api_key:
        return _make_outcome("serpapi", query, [], status=SearchStatus.CONFIG_MISSING)

    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "hl": _SERP_LANG_MAP.get(lang, "en"),
        "num": num,
    }

    last_exc: Exception | None = None
    for attempt in range(1 + _RETRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(_SERPAPI_URL, params=params)
                response.raise_for_status()
                data = response.json()

            hotel_pack = data.get("hotels_results", {})
            hotel_properties = hotel_pack.get("properties", [])
            if hotel_properties:
                structured: list[dict] = []
                for h in hotel_properties[:8]:
                    name = h.get("name", "")
                    price = h.get("rate_per_night", {}).get("lowest", "") or h.get("price", "")
                    rating = str(h.get("overall_rating", "")) or str(h.get("rating", ""))
                    address = h.get("address", "") or h.get("location", "")
                    link = h.get("link", "") or h.get("serpapi_property_link", "")
                    snippet = h.get("description", "") or h.get("snippet", "")
                    if name:
                        structured.append({
                            "title": name,
                            "link": _sanitize_url(link),
                            "snippet": snippet,
                            "price": str(price),
                            "rating": rating,
                            "address": address,
                            "_structured": True,
                        })
                if structured:
                    validated = _validate_results(structured, query=query, lang=lang)
                    logger.info("SerpAPI hotel pack", extra={"query": query[:50], "attempt": attempt + 1, "hotels": len(validated), "lang": lang})
                    if validated:
                        return _make_outcome("serpapi", query, validated)
                    return _make_outcome("serpapi", query, [], status=SearchStatus.FILTERED_OUT)

            raw_results = data.get("organic_results", [])
            results = [
                {"title": r.get("title", ""), "link": _sanitize_url(r.get("link", "")), "snippet": r.get("snippet", "")}
                for r in raw_results
            ]
            filtered = _filter_results(results, query=query, lang=lang)
            logger.info("SerpAPI search completed", extra={"query": query[:50], "attempt": attempt + 1, "raw": len(results), "filtered": len(filtered), "lang": lang})
            if filtered:
                return _make_outcome("serpapi", query, filtered)
            if results:
                return _make_outcome("serpapi", query, [], status=SearchStatus.FILTERED_OUT)
            return _make_outcome("serpapi", query, [], status=SearchStatus.NO_RESULTS)
        except Exception as exc:
            last_exc = exc
            logger.warning("SerpAPI attempt failed", extra={"query": query[:50], "attempt": attempt + 1, "error": str(exc)})
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("SerpAPI failed — falling back to SearXNG", extra={"query": query[:50], "error": str(last_exc)})
    return _make_outcome("serpapi", query, [], status=SearchStatus.PROVIDER_ERROR, error=str(last_exc) if last_exc else "")


async def _search_searxng(query: str, lang: str, num: int) -> SearchOutcome:
    base_url = settings.searxng_url
    if not base_url:
        return _make_outcome("searxng", query, [], status=SearchStatus.CONFIG_MISSING)

    params = {
        "q": query,
        "format": "json",
        "language": lang,
        "pageno": 1,
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
                {"title": r.get("title", ""), "link": _sanitize_url(r.get("url", "")), "snippet": r.get("content", "")}
                for r in raw
                if r.get("title") or r.get("content")
            ]
            filtered = _filter_results(results, query=query, lang=lang)
            logger.info("SearXNG search completed", extra={"query": query[:50], "attempt": attempt + 1, "raw": len(results), "filtered": len(filtered), "lang": lang})
            if filtered:
                return _make_outcome("searxng", query, filtered)
            if results:
                return _make_outcome("searxng", query, [], status=SearchStatus.FILTERED_OUT)
            return _make_outcome("searxng", query, [], status=SearchStatus.NO_RESULTS)
        except Exception as exc:
            last_exc = exc
            logger.warning("SearXNG attempt failed", extra={"query": query[:50], "attempt": attempt + 1, "error": str(exc)})
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

    logger.error("SearXNG failed — all providers exhausted", extra={"query": query[:50], "error": str(last_exc)})
    return _make_outcome("searxng", query, [], status=SearchStatus.PROVIDER_ERROR, error=str(last_exc) if last_exc else "")


class SearchService:
    async def search_with_status(self, query: str, lang: str = "en", num: int = 10) -> SearchOutcome:
        query = (query or "").strip()
        if not query:
            return SearchOutcome(results=[], status=SearchStatus.EMPTY_QUERY, provider="", error="", query="")

        query_for_search = _compose_search_query(query, lang)
        outcomes = [
            await _search_tavily(query_for_search, lang, num),
            await _search_serpapi(query_for_search, lang, num),
            await _search_searxng(query_for_search, lang, num),
        ]

        for outcome in outcomes:
            if outcome.status == SearchStatus.SUCCESS and outcome.results:
                return outcome

        provider_error = next((o for o in outcomes if o.status == SearchStatus.PROVIDER_ERROR), None)
        if provider_error is not None:
            return provider_error

        filtered_out = next((o for o in outcomes if o.status == SearchStatus.FILTERED_OUT), None)
        if filtered_out is not None:
            return filtered_out

        no_results = next((o for o in outcomes if o.status == SearchStatus.NO_RESULTS), None)
        if no_results is not None:
            return no_results

        config_missing = next((o for o in outcomes if o.status == SearchStatus.CONFIG_MISSING), None)
        if config_missing is not None:
            return config_missing

        return SearchOutcome(results=[], status=SearchStatus.NO_RESULTS, provider="", error="", query=query_for_search)

    async def search(self, query: str, lang: str = "en", num: int = 10) -> list[dict]:
        outcome = await self.search_with_status(query, lang=lang, num=num)
        return outcome.results

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        if not results:
            return ""

        header = "SEARCH RESULTS"
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

        lines = [header]
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. {r.get('title', '')}\n"
                f"   SNIPPET: {r.get('snippet', '')}\n"
                f"   SOURCE: {r.get('link', '')}"
            )
        return "\n\n".join(lines)


search_service = SearchService()