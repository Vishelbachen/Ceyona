from __future__ import annotations

import re

"""Deterministic history filtering for prompt assembly.

This keeps the prompt layer small by selecting only turns that are likely to
matter for the current request. It is intentionally conservative and does not
replace retrieval or memory.
"""

_WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿа-яА-ЯёЁ'’\-]{3,}", re.UNICODE)

# Small stopword set for better topical overlap. Intentionally tiny: this is a
# guardrail, not a language model.
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "about", "into", "your",
    "you", "are", "was", "were", "have", "has", "had", "can", "could", "would",
    "what", "when", "where", "how", "why", "which", "who", "whom", "whose",
    "это", "этот", "эта", "эти", "что", "как", "где", "когда", "почему", "кто",
    "какой", "какая", "какие", "какое", "про", "для", "или", "на", "из", "по",
}

_MAX_SELECTED_TURNS = 6
_MIN_HISTORY_OVERLAP = 0.18


_CLOSURE_MARKERS = {
    "thanks", "thank you", "thx", "ok thanks", "okay thanks", "got it", "gotcha",
    "i'll look it up myself", "i will look it up myself", "i'll find it myself",
    "never mind", "never mind thanks", "that's enough", "that is enough",
    "спасибо", "спс", "ладно спасибо", "я сам", "я сам найду", "дальше не надо",
    "неважно", "не надо", "достаточно", "хватит", "пока всё",
    "ok", "okay", "fine", "all good", "no thanks", "thanks anyway",
}


def _topic_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in _WORD_RE.findall(text.lower()):
        token = token.strip("'’-")
        if token and token not in _STOPWORDS:
            terms.add(token)
    return terms


def _turn_overlap(current_terms: set[str], turn_text: str) -> float:
    if not current_terms:
        return 0.0
    turn_terms = _topic_terms(turn_text)
    if not turn_terms:
        return 0.0
    common = current_terms & turn_terms
    if not common:
        return 0.0
    return len(common) / max(1, min(len(current_terms), len(turn_terms)))


def _is_closure_message(text: str) -> bool:
    normalized = (text or "").strip().casefold()
    if not normalized:
        return False
    for marker in _CLOSURE_MARKERS:
        marker = marker.casefold()
        if " " in marker:
            if marker in normalized:
                return True
        else:
            if re.search(rf"\b{re.escape(marker)}\b", normalized):
                return True
    return False


def select_relevant_history(user_message: str, history: list[dict] | None) -> list[dict] | None:
    if not history:
        return None

    if _is_closure_message(user_message):
        return None

    current_terms = _topic_terms(user_message)
    if not current_terms:
        return None

    scored: list[tuple[float, int, dict]] = []
    for idx, turn in enumerate(history):
        content = str(turn.get("content") or "")
        if not content.strip():
            continue

        overlap = _turn_overlap(current_terms, content)
        if overlap < _MIN_HISTORY_OVERLAP:
            continue

        # Earlier turns should not dominate unless they clearly match the topic.
        recency_bonus = 0.0
        if idx >= max(0, len(history) - 2):
            recency_bonus = 0.05

        scored.append((overlap + recency_bonus, idx, turn))

    if not scored:
        return None

    # Deterministic ordering:
    # 1) by original history position
    # 2) keep only the tail of the selection so prompt size stays bounded
    ordered = [turn for _, _, turn in sorted(scored, key=lambda item: item[1])]
    if len(ordered) > _MAX_SELECTED_TURNS:
        ordered = ordered[-_MAX_SELECTED_TURNS:]

    # Preserve exact original order and remove duplicate role/content pairs.
    result: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for turn in ordered:
        key = (str(turn.get("role", "")), str(turn.get("content", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(turn)

    return result or None