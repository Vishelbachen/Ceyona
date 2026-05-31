from __future__ import annotations

import re

from i18n.t import SUPPORTED_LANGS

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Deterministic post-processing step in the synthesizer pipeline.
# Position: after meta/correction, before finalize/truncate.
#
# Problem it solves:
#   retrieval brings English/multilingual snippets → LLM partially absorbs
#   their language → output leaks foreign terms even when system prompt says
#   "respond in Russian". This is not a model failure — it is a retrieval
#   contamination problem that must be cleaned at the output boundary.
#
# What this module does NOT do:
#   ✗ translate text
#   ✗ rewrite meaning
#   ✗ make routing decisions
#   ✗ detect intent
#   ✗ enforce policy
#
# What it does:
#   ✓ strip inline source attribution artifacts ("источник 3", "source 2")
#   ✓ remove garbled/non-ASCII URLs leaking into response text
#   ✓ normalise English transport/UI terms to target language equivalents
#   ✓ collapse any whitespace damage caused by the above substitutions
#
# Authority boundary:
#   This module never changes meaning. It only cleans surface artifacts.
#   If a substitution would change meaning → don't substitute.


# ─── SOURCE ATTRIBUTION ARTIFACTS ─────────────────────────────────────────────
# LLM sometimes echoes "(источник 3)" or "(source 2)" from formatted snippets.
# These are internal retrieval labels — not useful to the user.

_SOURCE_TAGS: list[re.Pattern] = [
    re.compile(r"\(источник\s+\d+\)", re.IGNORECASE),   # (источник 3)
    re.compile(r"\(source\s+\d+\)", re.IGNORECASE),      # (source 2)
    re.compile(r"\bисточник\s+\d+\b", re.IGNORECASE),   # источник 3 (without parens)
    re.compile(r"\bsource\s+\d+\b", re.IGNORECASE),     # source 2 (without parens)
]


# ─── GARBLED URL PATTERN ──────────────────────────────────────────────────────
# SerpAPI occasionally returns URLs with Unicode subscript/fullwidth chars.
# source_credibility filters these from retrieval, but LLM may still echo
# a garbled URL it saw in a snippet. Strip any URL containing non-ASCII in path.

_GARBLED_URL = re.compile(
    r"https?://[^\s]*[^\x00-\x7F][^\s]*",  # URL with non-ASCII character anywhere
    re.UNICODE,
)


# ─── LANGUAGE LEAK MAPS ───────────────────────────────────────────────────────
# Deterministic term substitution per target language.
# Only applied when target lang matches — never globally.
# Scope: common transport/UI terms that leak from English retrieval snippets.
#
# Rules for adding entries:
#   1. The English term must be a known retrieval artifact (seen in production)
#   2. The substitution must be semantically equivalent, not approximate
#   3. Never add terms that could appear in code, URLs, or proper nouns
#
# Each entry is case-insensitive — _smart_sub() restores original casing.
# One entry per term: no need for "Route"/"route" duplicates.

_LEAK_MAPS: dict[str, dict[str, str]] = {
    "ru": {
        "route":        "маршрут",
        "station":      "станция",
        "stop":         "остановка",
        "terminal":     "терминал",
        "departure":    "отправление",
        "arrival":      "прибытие",
        "platform":     "платформа",
        "traffic":      "пробки",
        "drive time":   "время в пути",
        "distance":     "расстояние",
        "directions":   "маршрут",
        "estimated":    "примерно",
    },
    "de": {
        "route":        "Route",
        "station":      "Station",
        "stop":         "Haltestelle",
        "departure":    "Abfahrt",
        "arrival":      "Ankunft",
        "platform":     "Gleis",
        "traffic":      "Verkehr",
        "drive time":   "Fahrzeit",
        "distance":     "Entfernung",
    },
    "fr": {
        "stop":         "arrêt",
        "departure":    "départ",
        "arrival":      "arrivée",
        "platform":     "quai",
        "traffic":      "trafic",
        "drive time":   "temps de trajet",
        "distance":     "distance",
        "route":        "itinéraire",
    },
    "it": {
        "route":        "percorso",
        "station":      "stazione",
        "stop":         "fermata",
        "departure":    "partenza",
        "arrival":      "arrivo",
        "platform":     "binario",
        "traffic":      "traffico",
        "drive time":   "tempo di percorrenza",
        "distance":     "distanza",
    },
    "pt": {
        "route":        "rota",
        "station":      "estação",
        "stop":         "paragem",
        "departure":    "partida",
        "arrival":      "chegada",
        "platform":     "plataforma",
        "traffic":      "trânsito",
        "drive time":   "tempo de viagem",
        "distance":     "distância",
    },
    "es": {
        "route":        "ruta",
        "station":      "estación",
        "stop":         "parada",
        "departure":    "salida",
        "arrival":      "llegada",
        "platform":     "andén",
        "traffic":      "tráfico",
        "drive time":   "tiempo de viaje",
        "distance":     "distancia",
    },
    "pl": {
        "route":        "trasa",
        "station":      "stacja",
        "stop":         "przystanek",
        "departure":    "odjazd",
        "arrival":      "przyjazd",
        "platform":     "peron",
        "traffic":      "ruch drogowy",
        "drive time":   "czas jazdy",
        "distance":     "odległość",
    },
    "uk": {
        "route":        "маршрут",
        "station":      "станція",
        "stop":         "зупинка",
        "departure":    "відправлення",
        "arrival":      "прибуття",
        "platform":     "платформа",
        "traffic":      "затори",
        "drive time":   "час у дорозі",
        "distance":     "відстань",
        "directions":   "маршрут",
    },
    "tr": {
        "stop":         "durak",
        "station":      "istasyon",
        "departure":    "kalkış",
        "arrival":      "varış",
        "platform":     "peron",
        "route":        "güzergah",
        "traffic":      "trafik",
        "drive time":   "seyahat süresi",
        "distance":     "mesafe",
    },
    "nl": {
        "route":        "route",
        "station":      "station",
        "stop":         "halte",
        "departure":    "vertrek",
        "arrival":      "aankomst",
        "platform":     "perron",
        "traffic":      "verkeer",
        "drive time":   "reistijd",
        "distance":     "afstand",
    },
    "sv": {
        "route":        "rutt",
        "station":      "station",
        "stop":         "hållplats",
        "departure":    "avgång",
        "arrival":      "ankomst",
        "platform":     "plattform",
        "traffic":      "trafik",
        "drive time":   "restid",
        "distance":     "avstånd",
    },
    "no": {
        "route":        "rute",
        "station":      "stasjon",
        "stop":         "holdeplass",
        "departure":    "avgang",
        "arrival":      "ankomst",
        "platform":     "plattform",
        "traffic":      "trafikk",
        "drive time":   "reisetid",
        "distance":     "avstand",
    },
    "da": {
        "route":        "rute",
        "station":      "station",
        "stop":         "stoppested",
        "departure":    "afgang",
        "arrival":      "ankomst",
        "platform":     "perron",
        "traffic":      "trafik",
        "drive time":   "rejsetid",
        "distance":     "afstand",
    },
    "fi": {
        "route":        "reitti",
        "station":      "asema",
        "stop":         "pysäkki",
        "departure":    "lähtö",
        "arrival":      "saapuminen",
        "platform":     "laituri",
        "traffic":      "liikenne",
        "drive time":   "matka-aika",
        "distance":     "etäisyys",
    },
    "cs": {
        "route":        "trasa",
        "station":      "stanice",
        "stop":         "zastávka",
        "departure":    "odjezd",
        "arrival":      "příjezd",
        "platform":     "nástupiště",
        "traffic":      "provoz",
        "drive time":   "doba jízdy",
        "distance":     "vzdálenost",
    },
    "sk": {
        "route":        "trasa",
        "station":      "stanica",
        "stop":         "zastávka",
        "departure":    "odchod",
        "arrival":      "príchod",
        "platform":     "nástupište",
        "traffic":      "premávka",
        "drive time":   "čas jazdy",
        "distance":     "vzdialenosť",
    },
    "ro": {
        "route":        "rută",
        "station":      "stație",
        "stop":         "oprire",
        "departure":    "plecare",
        "arrival":      "sosire",
        "platform":     "peron",
        "traffic":      "trafic",
        "drive time":   "timp de condus",
        "distance":     "distanță",
    },
    "hu": {
        "route":        "útvonal",
        "station":      "állomás",
        "stop":         "megálló",
        "departure":    "indulás",
        "arrival":      "érkezés",
        "platform":     "vágány",
        "traffic":      "forgalom",
        "drive time":   "menetidő",
        "distance":     "távolság",
    },
    "bg": {
        "route":        "маршрут",
        "station":      "гара",
        "stop":         "спирка",
        "departure":    "заминаване",
        "arrival":      "пристигане",
        "platform":     "перон",
        "traffic":      "трафик",
        "drive time":   "време за пътуване",
        "distance":     "разстояние",
    },
    "hr": {
        "route":        "ruta",
        "station":      "stanica",
        "stop":         "stajalište",
        "departure":    "polazak",
        "arrival":      "dolazak",
        "platform":     "peron",
        "traffic":      "promet",
        "drive time":   "vrijeme vožnje",
        "distance":     "udaljenost",
    },
    "sr": {
        "route":        "маршрута",
        "station":      "станица",
        "stop":         "станица",
        "departure":    "полазак",
        "arrival":      "долазак",
        "platform":     "перон",
        "traffic":      "саобраћај",
        "drive time":   "време вожње",
        "distance":     "удаљеност",
    },
    "vi": {
        "route":        "tuyến đường",
        "station":      "ga",
        "stop":         "điểm dừng",
        "departure":    "khởi hành",
        "arrival":      "đến nơi",
        "platform":     "sân ga",
        "traffic":      "giao thông",
        "drive time":   "thời gian lái xe",
        "distance":     "khoảng cách",
    },
    "id": {
        "route":        "rute",
        "station":      "stasiun",
        "stop":         "pemberhentian",
        "departure":    "keberangkatan",
        "arrival":      "kedatangan",
        "platform":     "peron",
        "traffic":      "lalu lintas",
        "drive time":   "waktu tempuh",
        "distance":     "jarak",
    },
    "ms": {
        "route":        "laluan",
        "station":      "stesen",
        "stop":         "perhentian",
        "departure":    "berlepas",
        "arrival":      "ketibaan",
        "platform":     "platform",
        "traffic":      "trafik",
        "drive time":   "masa memandu",
        "distance":     "jarak",
    },
    "hi": {
        "route":        "मार्ग",
        "station":      "स्टेशन",
        "stop":         "पड़ाव",
        "departure":    "प्रस्थान",
        "arrival":      "आगमन",
        "platform":     "प्लेटफार्म",
        "traffic":      "यातायात",
        "drive time":   "यात्रा समय",
        "distance":     "दूरी",
    },
    "ka": {
        "route":        "მარშრუტი",
        "station":      "სადგური",
        "stop":         "გაჩერება",
        "departure":    "გამგზავრება",
        "arrival":      "ჩამოსვლა",
        "traffic":      "საგზაო მოძრაობა",
        "distance":     "მანძილი",
    },
    "az": {
        "route":        "marşrut",
        "station":      "stansiya",
        "stop":         "dayanacaq",
        "departure":    "yola düşmə",
        "arrival":      "gəliş",
        "platform":     "platforma",
        "traffic":      "nəqliyyat",
        "drive time":   "yol müddəti",
        "distance":     "məsafə",
    },
    "kk": {
        "route":        "маршрут",
        "station":      "станция",
        "stop":         "аялдама",
        "departure":    "жөнелу",
        "arrival":      "келу",
        "traffic":      "жол қозғалысы",
        "distance":     "қашықтық",
    },
    "uz": {
        "route":        "marshrut",
        "station":      "stansiya",
        "stop":         "bekat",
        "departure":    "jo'nab ketish",
        "arrival":      "kelish",
        "traffic":      "transport",
        "distance":     "masofa",
    },
    "hy": {
        "route":        "երթուղի",
        "station":      "կայան",
        "stop":         "կանգառ",
        "departure":    "մեկնում",
        "arrival":      "ժամանում",
        "traffic":      "երթևեկություն",
        "distance":     "հեռավորություն",
    },
    "sw": {
        "route":        "njia",
        "station":      "kituo",
        "stop":         "kusimama",
        "departure":    "kuondoka",
        "arrival":      "kuwasili",
        "traffic":      "msongamano",
        "distance":     "umbali",
    },
}

# Languages where leak substitution is skipped entirely:
# EN — source language of leaks, not a target.
# JA/ZH/KO/AR/HE/FA/TH/KO — non-Latin scripts where English leaks
# are visually obvious and the model rarely produces them mid-sentence.
# BN/UR/MN/AM/HA/YO/IG/SO/PS/KU/UG/TT — no production leak evidence yet;
# add to _LEAK_MAPS if confirmed in Sentry.
_SKIP_SUBSTITUTION: frozenset[str] = frozenset({
    "en",
    "ja", "zh", "ko", "ar", "he", "fa", "th",
    "bn", "ur", "mn", "am", "ha", "yo", "ig", "so", "ps", "ku", "ug", "tt",
})

# Sanity check at import time: every lang in _LEAK_MAPS must be in SUPPORTED_LANGS.
_unknown = set(_LEAK_MAPS) - SUPPORTED_LANGS
if _unknown:
    raise ValueError(f"output_normalizer: _LEAK_MAPS contains unsupported langs: {_unknown}")


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _strip_source_tags(text: str) -> str:
    """Remove inline source attribution artifacts."""
    for pattern in _SOURCE_TAGS:
        text = pattern.sub("", text)
    return text


def _strip_garbled_urls(text: str) -> str:
    """Remove URLs containing non-ASCII characters."""
    return _GARBLED_URL.sub("", text)


def _smart_sub(text: str, en_term: str, native_term: str) -> str:
    """
    Case-insensitive substitution that restores the casing of the match.

    Rules:
      - ALL CAPS match  → native term uppercased
      - Title Case match → native term title-cased
      - lowercase match  → native term as-is (already lowercase in _LEAK_MAPS)

    For non-Latin native terms (Cyrillic, Georgian, etc.) title-casing
    is applied only to the first character — correct for all scripts.
    """
    pattern = re.compile(rf"\b{re.escape(en_term)}\b", re.IGNORECASE)

    def _replace(m: re.Match) -> str:
        matched = m.group(0)
        if matched.isupper():
            return native_term.upper()
        if matched[0].isupper():
            return native_term[0].upper() + native_term[1:]
        return native_term

    return pattern.sub(_replace, text)


def _apply_leak_map(text: str, lang: str) -> str:
    """
    Substitute known English leak terms with target language equivalents.
    Only runs for languages in _LEAK_MAPS. Skips _SKIP_SUBSTITUTION langs.
    """
    if lang in _SKIP_SUBSTITUTION:
        return text

    leak_map = _LEAK_MAPS.get(lang)
    if not leak_map:
        return text

    for en_term, native_term in leak_map.items():
        text = _smart_sub(text, en_term, native_term)

    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces left behind by removals."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─── VISION META OPENERS ─────────────────────────────────────────────────────
# When the response originates from vision, the model sometimes starts with a
# meta sentence ("I see that...", "Изображение показывает...") instead of
# answering the user. These are presentation artifacts, not meaning.
#
# This cleaner removes only the leading meta opening; it never rewrites the
# substantive answer that follows.
_VISION_META_PREFIXES: list[re.Pattern] = [
    re.compile(r"^\s*(?:Я\s+)?вижу,?\s+что\s+", re.IGNORECASE),
    re.compile(r"^\s*На\s+изображении\s+", re.IGNORECASE),
    re.compile(r"^\s*Изображение\s+(?:показывает|представляет\s+собой)\s+", re.IGNORECASE),
    re.compile(r"^\s*(?:I\s+)?see\s+that\s+", re.IGNORECASE),
    re.compile(r"^\s*The\s+(?:image|photo|picture)\s+(?:shows|depicts|contains)\s+", re.IGNORECASE),
    re.compile(r"^\s*This\s+(?:image|photo|picture)\s+(?:shows|depicts|contains)\s+", re.IGNORECASE),
]

def _strip_vision_meta_opening(text: str) -> str:
    if not text:
        return text
    result = text
    for pattern in _VISION_META_PREFIXES:
        if pattern.search(result):
            idx = result.find(".")
            if idx != -1 and idx < 220:
                result = result[idx + 1 :].lstrip()
            else:
                result = pattern.sub("", result, count=1).lstrip()
            break
    return result


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def apply(text: str, lang: str = "en", from_vision: bool = False) -> str:
    """
    Apply language output normalization.

    Called by response_synthesizer at step 6 (after correction, before finalize).
    Must never raise — caller keeps original on any exception.
    Must never change meaning — only clean surface artifacts.
    When from_vision=True, it also strips leading meta-openers that often appear
    in image descriptions.

    Pipeline:
      1. Strip source attribution tags  (источник 3, source 2)
      2. Strip garbled non-ASCII URLs
      3. Apply language leak map        (English transport terms → native)
      4. Collapse whitespace

    Returns normalised text. If result is empty, returns original.
    """
    if not text or not text.strip():
        return text

    result = _strip_source_tags(text)
    result = _strip_garbled_urls(result)
    result = _apply_leak_map(result, lang)

    if from_vision:
        result = _strip_vision_meta_opening(result)

    result = _collapse_whitespace(result)

    return result if result.strip() else text