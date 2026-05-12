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
    # Extended 鈥� fallback to English for SerpAPI
    "ha": "en", "yo": "en", "ig": "en", "so": "so",
    "ku": "en", "ps": "en", "ug": "en", "tt": "en",
}


class SearchService:
    """
    SerpAPI web search client.
    Read-only. No state. No interpretation.
    Returns raw results 鈥� caller formats them.
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
                "en": "馃攳 No results found.",
                "ru": "馃攳 袪械蟹褍谢褜褌邪褌褘 薪械 薪邪泄写械薪褘.",
                "de": "馃攳 Keine Ergebnisse gefunden.",
                "fr": "馃攳 Aucun r茅sultat trouv茅.",
                "es": "馃攳 No se encontraron resultados.",
                "pt": "馃攳 Nenhum resultado encontrado.",
                "it": "馃攳 Nessun risultato trovato.",
                "tr": "馃攳 Sonu莽 bulunamad谋.",
                "ar": "馃攳 賱賲 賷鬲賲 丕賱毓孬賵乇 毓賱賶 賳鬲丕卅噩.",
                "zh": "馃攳 鏈壘鍒扮粨鏋溿€�",
                "ja": "馃攳 绲愭灉銇岃銇ゃ亱銈娿伨銇涖倱銇с仐銇熴€�",
                "ko": "馃攳 瓴瓣臣毳� 彀眷潉 靾� 鞐嗢姷雼堧嫟.",
                "pl": "馃攳 Nie znaleziono wynik贸w.",
                "uk": "馃攳 袪械蟹褍谢褜褌邪褌懈 薪械 蟹薪邪泄写械薪芯.",
                "fa": "馃攳 賳鬲蹖噩賴鈥屫й� 蹖丕賮鬲 賳卮丿.",
                "nl": "馃攳 Geen resultaten gevonden.",
                "sv": "馃攳 Inga resultat hittades.",
                "no": "馃攳 Ingen resultater funnet.",
                "da": "馃攳 Ingen resultater fundet.",
                "fi": "馃攳 Tuloksia ei l枚ydy.",
                "he": "馃攳 诇讗 谞诪爪讗讜 转讜爪讗讜转.",
                "hi": "馃攳 啶曕啶� 啶ぐ啶苦ぃ啶距ぎ 啶ㄠす啷€啶� 啶た啶侧ぞ啷�",
                "id": "馃攳 Tidak ada hasil ditemukan.",
                "ms": "馃攳 Tiada keputusan ditemui.",
                "th": "馃攳 喙勦浮喙堗笧喔氞笢喔ム弗喔编笧喔樴箤",
                "vi": "馃攳 Kh么ng t矛m th岷 k岷縯 qu岷�.",
                "ka": "馃攳 醿ㄡ償醿撫償醿掅償醿戓儤 醿曖償醿� 醿涐儩醿樶儷醿斸儜醿溼儛.",
                "hy": "馃攳 员謤栅盏崭謧斩謩斩榨謤 展榨斩 眨湛斩站榨宅:",
                "az": "馃攳 N蓹tic蓹 tap谋lmad谋.",
                "kk": "馃攳 袧訖褌懈卸械 褌邪斜褘谢屑邪写褘.",
                "uz": "馃攳 Natija topilmadi.",
                "mn": "馃攳 耶褉 写爷薪 芯谢写褋芯薪谐爷泄.",
                "sw": "馃攳 Hakuna matokeo yaliyopatikana.",
                "am": "馃攳 釄濁姇釄� 釈嶀尋釅� 釆犪垗釅搬寛釆樶垵釐�",
                "bg": "馃攳 袧械 褋邪 薪邪屑械褉械薪懈 褉械蟹褍谢褌邪褌懈.",
                "hr": "馃攳 Nisu prona膽eni rezultati.",
                "sr": "馃攳 袧懈褋褍 锌褉芯薪邪褣械薪懈 褉械蟹褍谢褌邪褌懈.",
                "cs": "馃攳 沤谩dn茅 v媒sledky nenalezeny.",
                "sk": "馃攳 沤iadne v媒sledky sa nena拧li.",
                "ro": "馃攳 Nu s-au g膬sit rezultate.",
                "hu": "馃攳 Nem tal谩lhat贸k eredm茅nyek.",
                "bn": "馃攳 唳曕唳ㄠ 唳Σ唳距Λ唳� 唳唳撪Ο唳监 唳唳唳ㄠ啷�",
                "ur": "馃攳 讴賵卅蹖 賳鬲蹖噩蹃 賳蹃蹖诤 賲賱丕蹟",
                "ha": "馃攳 Ba a sami sakamakon ba.",
                "yo": "馃攳 Ko si abajade ti a ri.",
                "so": "馃攳 Natiijooyin lama helin.",
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