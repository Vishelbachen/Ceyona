from __future__ import annotations

import re

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

_LEAK_MAPS: dict[str, dict[str, str]] = {
    "ru": {
        # Transport terms leaking from English routing sources
        "route":        "маршрут",
        "Route":        "Маршрут",
        "station":      "станция",
        "Station":      "Станция",
        "stop":         "остановка",
        "Stop":         "Остановка",
        "terminal":     "терминал",
        "Terminal":     "Терминал",
        "departure":    "отправление",
        "Departure":    "Отправление",
        "arrival":      "прибытие",
        "Arrival":      "Прибытие",
        "platform":     "платформа",
        "Platform":     "Платформа",
        # UI/navigation terms
        "directions":   "маршрут",
        "Directions":   "Маршрут",
    },
    "de": {
        "route":        "Route",
        "station":      "Station",
        "stop":         "Haltestelle",
        "Stop":         "Haltestelle",
        "departure":    "Abfahrt",
        "arrival":      "Ankunft",
        "platform":     "Gleis",
    },
    "fr": {
        "stop":         "arrêt",
        "Stop":         "Arrêt",
        "departure":    "départ",
        "Departure":    "Départ",
        "arrival":      "arrivée",
        "Arrival":      "Arrivée",
        "platform":     "quai",
        "Platform":     "Quai",
    },
    "tr": {
        "stop":         "durak",
        "Stop":         "Durak",
        "station":      "istasyon",
        "Station":      "İstasyon",
        "departure":    "kalkış",
        "arrival":      "varış",
        "platform":     "peron",
    },
    "uk": {
        "route":        "маршрут",
        "Route":        "Маршрут",
        "station":      "станція",
        "Station":      "Станція",
        "stop":         "зупинка",
        "Stop":         "Зупинка",
        "departure":    "відправлення",
        "arrival":      "прибуття",
        "platform":     "платформа",
    },
}

# Languages where we skip leak substitution entirely:
# EN is the source language of leaks, not a target.
# JA/AR/ZH/KO have such different scripts that English leaks are visually
# obvious and model rarely produces them mid-sentence.
_SKIP_SUBSTITUTION: frozenset[str] = frozenset({
    "en", "ja", "ar", "zh", "ko", "he", "fa",
})


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _strip_source_tags(text: str) -> str:
    """Remove inline source attribution artifacts."""
    for pattern in _SOURCE_TAGS:
        text = pattern.sub("", text)
    return text


def _strip_garbled_urls(text: str) -> str:
    """Remove URLs containing non-ASCII characters."""
    return _GARBLED_URL.sub("", text)


def _apply_leak_map(text: str, lang: str) -> str:
    """
    Substitute known English leak terms with target language equivalents.
    Only runs for languages in _LEAK_MAPS. Skips _SKIP_SUBSTITUTION langs.
    Uses word-boundary matching to avoid partial substitutions.
    """
    if lang in _SKIP_SUBSTITUTION:
        return text

    leak_map = _LEAK_MAPS.get(lang)
    if not leak_map:
        return text

    for en_term, native_term in leak_map.items():
        # Word boundary: don't match inside longer words or URLs
        pattern = re.compile(rf"\b{re.escape(en_term)}\b")
        text = pattern.sub(native_term, text)

    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces left behind by removals."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def apply(text: str, lang: str = "en") -> str:
    """
    Apply language output normalization.

    Called by response_synthesizer at step 6 (after correction, before finalize).
    Must never raise — caller keeps original on any exception.
    Must never change meaning — only clean surface artifacts.

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
    result = _collapse_whitespace(result)

    return result if result.strip() else text