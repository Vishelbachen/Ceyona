from __future__ import annotations

import re

"""Deterministic history filtering for prompt assembly.

This keeps the prompt layer small by selecting only turns that are likely to
matter for the current request. It is intentionally conservative and does not
replace retrieval or memory.
"""

_WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿа-яА-ЯёЁ'’\-]{3,}", re.UNICODE)

# Tiny stopword set to improve topical overlap. Intentionally small: this is a
# guardrail, not semantic parsing.
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "about", "into", "your",
    "you", "are", "was", "were", "have", "has", "had", "can", "could", "would",
    "what", "when", "where", "how", "why", "which", "who", "whom", "whose",
    "please", "help", "need", "want", "show", "tell",
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


def _turn_boost(turn_text: str) -> float:
    """
    Lightweight signal boost for structurally important turns.
    Keeps the selector deterministic and cheap.
    """
    boost = 0.0
    stripped = turn_text.strip()
    if not stripped:
        return boost

    if "```" in stripped or "`" in stripped:
        boost += 0.08
    if "http://" in stripped or "https://" in stripped or "www." in stripped:
        boost += 0.05
    if any(ch.isdigit() for ch in stripped):
        boost += 0.03
    if len(stripped.split()) <= 6:
        boost += 0.02
    return boost


def select_relevant_history(user_message: str, history: list[dict] | None) -> list[dict] | None:
    """
    Select a compact, order-preserving slice of history for prompt assembly.

    Strategy:
      1. Always keep the most recent turns.
      2. Pull in older turns that overlap topically with the current message.
      3. Preserve original chronological order.
      4. Return None when nothing is worth passing through.

    This is a selector only. It does not summarize, rewrite, or store memory.
    """
    if not history:
        return None

    current_terms = _topic_terms(user_message)
    short_form = len(user_message.split()) <= 8
    keep_recent = 4 if short_form else 2

    recent = history[-keep_recent:] if keep_recent > 0 else []
    older = history[:-keep_recent] if len(history) > keep_recent else []

    scored: list[tuple[float, dict]] = []

    for turn in recent:
        content = str(turn.get("content") or "")
        if not content.strip():
            continue
        scored.append((1.0, turn))

    for turn in older:
        content = str(turn.get("content") or "")
        if not content.strip():
            continue
        overlap = _turn_overlap(current_terms, content)
        if overlap <= 0.0:
            continue
        score = overlap + _turn_boost(content)
        if score >= 0.18:
            scored.append((score, turn))

    if not scored:
        return None

    ordered: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # Preserve the original conversation order.
    for turn in history:
        key = (str(turn.get("role", "")), str(turn.get("content", "")))
        if key in seen:
            continue
        if any(turn is candidate for _, candidate in scored):
            ordered.append(turn)
            seen.add(key)

    return ordered or None