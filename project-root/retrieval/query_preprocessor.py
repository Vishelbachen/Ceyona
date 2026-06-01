from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

try:
    from unidecode import unidecode
except Exception:  # pragma: no cover - optional dependency fallback
    def unidecode(text: str) -> str:  # type: ignore[misc]
        return text

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional dependency fallback
    fuzz = None  # type: ignore[assignment]


_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_TO_SPACE_RE = re.compile(r"""[‐-―\-_/\|•·,;:!?()\[\]{}<>\"'`~^=*+]+""")
_BOUNDARY_CUES = (
    " and ", " or ", " but ", " yet ", " however ", " because ", " so ",
    " и ", " или ", " а ", " но ", " также ", " ещё ",
    " und ", " oder ", " aber ", " sowie ",
    " y ", " o ", " pero ", " aunque ",
    " et ", " ou ", " mais ",
    " ثم ", " أو ", " لكن ",
    " また ", " そして ", " あるいは ",
    " 그리고 ", " 또는 ",
)

_GEO_CUES = (
    " city center of ", " city centre of ", " center of ", " centre of ",
    " downtown of ", " in the center of ", " in the centre of ",
    " in center of ", " in centre of ", " near ", " around ", " close to ",
    " within ", " at ", " in ", " to ", " from ", " for ", " of ",
    " в центре ", " в центре", " в ", " во ", " около ", " возле ", " рядом с ",
    " из ", " до ", " к ", " на ",
    " centrum ", " centro de ", " centro ", " centro di ", " centre de ",
    " centre ", " center ", " downtown ", " near ",
    " cerca de ", " en ", " dans ", " à ", " au ", " aux ", " bei ", " im ", " in ",
    " şehir ", " şehir merkezi ", " merkez ", " centro storico ",
)

_LEADING_GEO_MODIFIERS = {
    "center", "centre", "central", "downtown", "midtown", "uptown",
    "city", "citycenter", "citycentre", "inner", "innercity", "old", "town",
    "центр", "центре", "центра", "город", "городе", "города",
    "centrum", "centro", "centrode", "centrodi",
    "area", "district", "districts",
    "città", "citta", "centreville",
    "内", "市", "中心", "市中心", "市內", "市内", "都心",
}

_HOTEL_MARKERS = {
    "hotel", "hotels", "otel", "motel", "hostel", "guesthouse", "lodging",
    "accommodation", "apartments", "apartment", "suite", "resort", "bnb",
    "отель", "отели", "гостиница", "гостиницы", "хостел", "апартаменты",
    "飯店", "酒店", "旅館", "ホテル", "宿", "民宿", "게스트하우스",
    "hotelu", "hôtel", "albergo", "auberge", "숙소",
}

_TRAVEL_MARKERS = {
    "route", "routes", "directions", "how to get", "how do i get", "go to",
    "travel", "trip", "visit", "airport", "station", "metro", "subway",
    "taxi", "bus", "train", "tram", "ferry", "flight", "transport",
    "маршрут", "как добраться", "как доехать", "добраться", "поезд", "автобус",
    "метро", "такси", "аэропорт", "вокзал", "станция", "дорога", "поехать",
    "行き方", "行く", "空港", "駅", "交通", "路线", "怎么去", "机场", "地铁",
}

_SEARCH_FOCUS_MARKERS = {
    "cheap", "budget", "best", "top", "good", "nice", "nearest", "closest",
    "дешев", "лучшие", "лучший", "бюджет", "недорог", "самые", "топ",
    "bon", "meilleur", "meilleurs", "barato", "económico", "wirtschaftlich",
    "preiswert", "günstig", "obere", "优先", "便宜", "最佳", "便捷",
}

_MAX_LOCATION_TOKENS = 8
_LOCATION_NEGATIVE_CUES = (
    " what ", " which ", " who ", " when ", " where ", " why ", " how ",
    " best ", " popular ", " famous ", " recommend ", " suggestion ",
    " можно ", " можете ", " можешь ", " какой ", " какая ", " какое ",
    " что ", " посовет", " совет",
)


def _looks_like_location(candidate: str) -> bool:
    candidate = _normalize_text(candidate)
    if not candidate:
        return False
    if len(candidate.split()) > _MAX_LOCATION_TOKENS:
        return False
    if "?" in candidate or "!" in candidate:
        return False
    folded = f" {_ascii_fold(candidate)} "
    if any(cue in folded for cue in _LOCATION_NEGATIVE_CUES):
        return False
    if any(ch.isdigit() for ch in candidate):
        return False
    return True


_DEFAULT_LANGUAGE = "en"


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _ascii_fold(text: str) -> str:
    folded = unidecode(_normalize_text(text))
    folded = unicodedata.normalize("NFKC", folded)
    folded = folded.casefold()
    folded = _PUNCT_TO_SPACE_RE.sub(" ", folded)
    folded = _WHITESPACE_RE.sub(" ", folded).strip()
    return folded


def _contains_marker(text: str, markers: set[str]) -> bool:
    folded = _ascii_fold(text)
    raw = _normalize_text(text).casefold()
    return any(marker in folded or marker in raw for marker in markers)


def _truncate_at_boundary(text: str) -> str:
    text = text.strip()
    if not text:
        return text

    lower = text.casefold()
    cut = len(text)
    for cue in _BOUNDARY_CUES:
        idx = lower.find(cue)
        if idx > 0:
            cut = min(cut, idx)
    return text[:cut].strip(" ,.;:!?\t\n\r")


def _strip_leading_modifiers(candidate: str) -> str:
    text = _normalize_text(candidate)
    if not text:
        return ""

    tokens = [t for t in re.split(r"\s+", text) if t]
    if not tokens:
        return ""

    def folded_token(token: str) -> str:
        return _ascii_fold(token).replace(" ", "")

    idx = 0
    while idx < len(tokens):
        token = folded_token(tokens[idx])
        if token in _LEADING_GEO_MODIFIERS:
            idx += 1
            continue
        if idx + 1 < len(tokens):
            pair = f"{token} {folded_token(tokens[idx + 1])}"
            if pair in _LEADING_GEO_MODIFIERS:
                idx += 2
                continue
        break

    cleaned = " ".join(tokens[idx:]).strip(" ,.;:!?\t\n\r")
    return cleaned


def _candidate_from_cues(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    lower = normalized.casefold()
    best = ""

    for cue in sorted(_GEO_CUES, key=len, reverse=True):
        idx = lower.rfind(cue)
        if idx < 0:
            continue
        candidate = normalized[idx + len(cue):]
        candidate = _truncate_at_boundary(candidate)
        candidate = _strip_leading_modifiers(candidate)
        if len(candidate) > len(best):
            best = candidate

    return best.strip()


def _extract_location(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    candidate = _candidate_from_cues(normalized)

    if not candidate and _contains_marker(normalized, _HOTEL_MARKERS | _TRAVEL_MARKERS):
        tail = _truncate_at_boundary(normalized)
        parts = [p for p in re.split(r"[,.!?;:/\]", tail) if p.strip()]
        if parts:
            candidate = parts[0].strip()

    candidate = _strip_leading_modifiers(candidate)
    candidate = _truncate_at_boundary(candidate)
    candidate = _normalize_text(candidate)

    # Prefer no location over a long or interrogative fragment.
    if candidate and not _looks_like_location(candidate):
        return ""

    return candidate


def _location_aliases(location: str) -> tuple[str, ...]:
    if not location:
        return ()

    aliases = []
    for variant in (
        location,
        _ascii_fold(location),
        _normalize_text(location).casefold(),
    ):
        variant = _WHITESPACE_RE.sub(" ", variant).strip()
        if variant and variant not in aliases:
            aliases.append(variant)
    return tuple(aliases)


def _detect_query_kind(text: str) -> str:
    if _contains_marker(text, _TRAVEL_MARKERS):
        return "travel"
    if _contains_marker(text, _HOTEL_MARKERS):
        return "hotel"
    if _contains_marker(text, _SEARCH_FOCUS_MARKERS):
        return "discovery"
    return "generic"


@dataclass(frozen=True)
class QueryProfile:
    raw_text: str
    normalized_text: str
    lang: str
    query_kind: str
    location: str
    location_ascii: str
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    keywords_ascii: tuple[str, ...]
    is_geo_query: bool


def normalize_query(text: str) -> str:
    """Normalize query text before retrieval/search. Deterministic. No I/O."""
    return _normalize_text(text)[:512]


@lru_cache(maxsize=2048)
def extract_query_profile(text: str, lang: str | None = None) -> QueryProfile:
    normalized = normalize_query(text)
    query_kind = _detect_query_kind(normalized)
    location = _extract_location(normalized) if query_kind in {"hotel", "travel"} else ""
    location_ascii = _ascii_fold(location) if location else ""
    aliases = _location_aliases(location)

    normalized_folded = _ascii_fold(normalized)
    location_folded = _ascii_fold(location)
    keywords = tuple(
        token for token in normalized.split(" ")
        if token and token.casefold() not in {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at"}
    )
    keywords_ascii = tuple(token for token in normalized_folded.split(" ") if token)
    if location_folded:
        keywords_ascii = tuple(token for token in keywords_ascii if token not in set(location_folded.split()))

    return QueryProfile(
        raw_text=text,
        normalized_text=normalized,
        lang=(lang or _DEFAULT_LANGUAGE),
        query_kind=query_kind,
        location=location,
        location_ascii=location_ascii,
        aliases=aliases,
        keywords=keywords,
        keywords_ascii=keywords_ascii,
        is_geo_query=bool(location) or query_kind in {"hotel", "travel"},
    )


def _best_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    if a in b or b in a:
        return 1.0

    if fuzz is None:
        a_tokens = set(a.split())
        b_tokens = set(b.split())
        if not a_tokens or not b_tokens:
            return 0.0
        return len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)

    return max(
        fuzz.partial_ratio(a, b) / 100.0,
        fuzz.token_set_ratio(a, b) / 100.0,
    )


def geo_relevance_score(query: str, candidate_text: str, lang: str | None = None) -> float:
    """
    Return a 0..1 affinity score for location-sensitive queries.
    Uses transliteration-aware matching so the score remains fair across
    languages and scripts.
    """
    profile = extract_query_profile(query, lang)
    if not profile.location:
        return 0.0

    candidate = _normalize_text(candidate_text)
    if not candidate:
        return 0.0

    candidate_variants = {
        candidate,
        candidate.casefold(),
        _ascii_fold(candidate),
    }
    best = 0.0
    for alias in profile.aliases:
        for variant in candidate_variants:
            best = max(best, _best_ratio(alias, variant))
            if best >= 1.0:
                return 1.0
    return best


def matches_location(
    query: str,
    candidate_text: str,
    lang: str | None = None,
    threshold: float = 0.56,
) -> bool:
    return geo_relevance_score(query, candidate_text, lang=lang) >= threshold


def preprocess(text: str) -> str:
    """
    Backwards-compatible query normalization helper.
    """
    return normalize_query(text)