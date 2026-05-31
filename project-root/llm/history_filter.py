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


def select_relevant_history(user_message: str, history: list[dict] | None) -> list[dict] | None:
    if not history:
        return None

    current_terms = _topic_terms(user_message)
    short_form = len(user_message.split()) <= 8
    keep_recent = 4 if short_form else 2

    recent = history[-keep_recent:] if keep_recent > 0 else []
    older = history[:-keep_recent] if len(history) > keep_recent else []

    selected: list[dict] = list(recent)
    for turn in older:
        content = str(turn.get("content") or "")
        if not content.strip():
            continue
        if _turn_overlap(current_terms, content) >= 0.18:
            selected.append(turn)

    if not selected:
        return None

    ordered: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for turn in history:
        key = (str(turn.get("role", "")), str(turn.get("content", "")))
        if key in seen:
            continue
        if turn in selected:
            ordered.append(turn)
            seen.add(key)

    return ordered or None