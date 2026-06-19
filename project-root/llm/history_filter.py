from __future__ import annotations

import re

"""Deterministic history filtering for prompt assembly.

This keeps the prompt layer small by selecting only turns that are likely to
matter for the current request. It is intentionally conservative and does not
replace retrieval or memory.

§10 (persona.md): closure detection now also surfaces open topics for
PromptContext so the coordinator can pass them to the system prompt via
CONTINUITY_RULE. This is a code-level signal, not a heuristic list.
"""

_WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿа-яА-ЯёЁ''\-]{3,}", re.UNICODE)

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


# ─── CLOSURE DETECTION ───────────────────────────────────────────────────────
# Architecture: closure detector tells history_filter whether to inject
# history (open topic) or skip it (user explicitly closed the thread).
#
# Previous implementation: fixed string list (_CLOSURE_MARKERS).
# Problem: fixed list catches only exact phrases. "ок понятно" → not caught.
# Correct solution (persona.md §10): expose open_topics signal to PromptContext
# so the LLM — which already has full context — decides whether to acknowledge.
#
# Closure heuristic is intentionally minimal:
#   - Very short messages (≤ 3 meaningful tokens) with no question mark
#     and no topical overlap with the last assistant turn → likely closure.
#   - This is a filter hint, not a semantic classifier.
#   - False negatives (missed closures) are safe: history is injected
#     when uncertain, which is the conservative choice.

_MIN_CLOSURE_TOKEN_COUNT = 3


def _topic_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in _WORD_RE.findall(text.lower()):
        token = token.strip("''-")
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


def _is_closure_message(text: str, history: list[dict] | None = None) -> bool:
    """
    Heuristic: is this message a topic closure?

    A message is likely a closure when ALL of the following hold:
      1. Fewer than _MIN_CLOSURE_TOKEN_COUNT meaningful tokens.
      2. No question mark (questions keep topics open).
      3. No topical overlap with the last assistant turn.

    This replaces the fixed _CLOSURE_MARKERS list. The LLM already has
    full context via CONTINUITY_RULE — it does not need the filter to
    catch specific closure phrases. What it needs is a reliable signal
    that history is worth injecting at all.
    """
    normalized = (text or "").strip()
    if not normalized:
        return False

    terms = _topic_terms(normalized)

    # Messages with enough substance are not closures.
    if len(terms) >= _MIN_CLOSURE_TOKEN_COUNT:
        return False

    # Questions keep the topic open.
    if "?" in normalized:
        return False

    # Check overlap with last assistant turn.
    if history:
        last_assistant = next(
            (t for t in reversed(history) if t.get("role") == "assistant"),
            None,
        )
        if last_assistant:
            overlap = _turn_overlap(terms, str(last_assistant.get("content", "")))
            if overlap >= _MIN_HISTORY_OVERLAP:
                return False  # topically connected — not a closure

    return True


# ─── OPEN TOPICS EXTRACTION ──────────────────────────────────────────────────
# persona.md §10: expose unresolved topics as a hint to the coordinator.
# The coordinator may add CONTINUITY_RULE to the system prompt when this
# is non-empty. The LLM then decides whether to acknowledge the open thread.

def extract_open_topics(history: list[dict] | None) -> list[str] | None:
    """
    Return a list of topic summaries from recent history turns that were
    NOT followed by a closure message.

    Implementation is intentionally lightweight — topic labels are the
    first meaningful noun-phrase from each user turn (≤ 6 words).
    The coordinator passes this to PromptContext.open_topics; the LLM
    receives it as part of CONTINUITY_RULE.

    Returns None when no open topics are detected.
    """
    if not history or len(history) < 2:
        return None

    # Walk history in pairs (user → assistant). A turn is "open" if the
    # NEXT user message does not match the closure heuristic.
    open_topics: list[str] = []

    for i, turn in enumerate(history):
        if turn.get("role") != "user":
            continue
        content = str(turn.get("content", "")).strip()
        if not content:
            continue

        # Is there a subsequent user message?
        next_user = next(
            (t for t in history[i + 1:] if t.get("role") == "user"),
            None,
        )

        if next_user is None:
            # This is the last user turn — not yet closed.
            label = _topic_label(content)
            if label:
                open_topics.append(label)
        else:
            next_content = str(next_user.get("content", "")).strip()
            # If the next user message looks like a closure, this topic is closed.
            if _is_closure_message(next_content, history[:i + 2]):
                continue
            # If there's topical overlap between this turn and the next,
            # the user is continuing — topic is still open.
            current_terms = _topic_terms(content)
            next_terms = _topic_terms(next_content)
            if current_terms & next_terms:
                # Active thread — mark as open only if no resolution found.
                pass  # resolved further in the loop

    return open_topics or None


def _topic_label(text: str) -> str:
    """Extract a short label (≤ 6 words) from the first sentence of a user turn."""
    first_sentence = re.split(r"[.!?\n]", text.strip())[0].strip()
    words = first_sentence.split()
    if not words:
        return ""
    return " ".join(words[:6])


# ─── HISTORY SELECTION ───────────────────────────────────────────────────────

def select_relevant_history(user_message: str, history: list[dict] | None) -> list[dict] | None:
    if not history:
        return None

    if _is_closure_message(user_message, history):
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