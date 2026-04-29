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
    "pl": "pl", "uk": "uk", "fa": "fa",
}


class SearchService:
    """
    SerpAPI web search client.
    Read-only. No state. No interpretation.
    Returns raw results — caller formats them.
    """

    def __init__(self) -> None:
        self._api_key = settings.serpapi_key

    async def search(
        self,
        query: str,
        lang: str = "en",
        num: int = 5,
    ) -> list[dict]:
        """
        Perform web search.
        Returns list of organic result dicts with keys:
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
                results = data.get("organic_results", [])
                logger.info("Search completed", extra={
                    "query": query[:50],
                    "results": len(results),
                    "lang": lang,
                })
                return [
                    {
                        "title": r.get("title", ""),
                        "link": r.get("link", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    for r in results
                ]
        except Exception as exc:
            logger.error("SearchService.search failed", extra={
                "query": query[:50],
                "error": str(exc),
            })
            return []

    def format_results(self, results: list[dict], lang: str = "en") -> str:
        """
        Format search results into Telegram-ready Markdown.
        Pure function. No I/O.
        """
        if not results:
            _no_results: dict[str, str] = {
                "en": "🔍 No results found.",
                "ru": "🔍 Результаты не найдены.",
                "de": "🔍 Keine Ergebnisse gefunden.",
                "fr": "🔍 Aucun résultat trouvé.",
                "es": "🔍 No se encontraron resultados.",
                "pt": "🔍 Nenhum resultado encontrado.",
                "it": "🔍 Nessun risultato trovato.",
                "tr": "🔍 Sonuç bulunamadı.",
                "ar": "🔍 لم يتم العثور على نتائج.",
                "zh": "🔍 未找到结果。",
                "ja": "🔍 結果が見つかりませんでした。",
                "ko": "🔍 결과를 찾을 수 없습니다.",
                "pl": "🔍 Nie znaleziono wyników.",
                "uk": "🔍 Результати не знайдено.",
                "fa": "🔍 نتیجه‌ای یافت نشد.",
            }
            return _no_results.get(lang, _no_results["en"])

        lines: list[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            lines.append(f"*{i}. [{title}]({link})*\n{snippet}")

        return "\n\n".join(lines)


# Singleton
search_service = SearchService()