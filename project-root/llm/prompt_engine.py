from __future__ import annotations

from dataclasses import dataclass

from contracts.shared_types import TruthMode
from i18n.t import lang_instruction as _lang_instruction
import re

# ─── HISTORY FILTERING ───────────────────────────────────────────────────────
# Keep only the conversation turns that are likely to matter for the current
# request. This is a deterministic guard against topic drift: a new task should
# not inherit unrelated older turns just because they are still in the chat log.
#
# The filter is intentionally conservative:
# - keep the latest 2 turns unconditionally (short-term continuity)
# - keep older turns only when they overlap with the current request
# - if the current request is short, preserve a slightly wider window
#
# This does not replace retrieval or memory; it only narrows raw chat history
# before prompt assembly.
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

def _select_relevant_history(user_message: str, history: list[dict] | None) -> list[dict] | None:
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

# ─── TRUTH ENFORCEMENT PROMPTS ───────────────────────────────────────────────
# STRICT: for intents where only retrieved data is valid (maps, poi, routes).
# HYBRID: for intents where context grounds the answer but LLM can clarify.
# GENERATIVE: no truth block — conversation/emotional/creative don't use retrieval.

_TRUTH_STRICT = (
    "The context below contains the only facts available for this request. "
    "Output only what is explicitly present in it — do not add, estimate, or infer. "
    "If the context is empty or incomplete — say so directly instead of filling the gap."
)

# TRUTH_HYBRID deliberately removed.
# Rationale: HYBRID intents (QUESTION, ANALYSIS, INSTRUCTION) receive retrieved
# context injected directly into the user turn — the model reads it as part of
# the input, not as a named object. Adding an explicit "use the context" layer
# turns context into a "semantic object of discourse" (ChatGPT analysis, May 2026)
# and causes the model to narrate its reasoning about the context instead of
# simply answering. STRICT is kept for intents where hallucination is
# architecturally forbidden (MAPS, WEATHER, SEARCH). See audit.md §session-4.


@dataclass(frozen=True)
class PromptContext:
    user_message: str
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    truth_mode: TruthMode = TruthMode.HYBRID
    lang: str = "en"


def build_messages(ctx: PromptContext) -> list[dict]:
    messages: list[dict] = []

    system_parts: list[str] = []

    # ── language instruction (always first) ───────────────────────────────────
    system_parts.append(_lang_instruction(ctx.lang))

    # ── intent-specific system prompt (second — model knows who it is first) ──
    if ctx.system_prompt:
        system_parts.append(ctx.system_prompt)

    # ── truth enforcement (STRICT intents only) ───────────────────────────────
    # STRICT: MAPS, WEATHER, SEARCH — hallucination architecturally forbidden.
    #         Explicit "use only the context" instruction is required.
    # HYBRID: QUESTION, ANALYSIS, INSTRUCTION — retrieved context is injected
    #         directly into the user turn as raw text (no label). The model reads
    #         it as part of the input without being told "this is context".
    #         No truth block needed — adding one creates meta-awareness loop.
    # GENERATIVE: CONVERSATION, EMOTIONAL, CREATIVE — no retrieval, no block.
    if ctx.truth_mode == TruthMode.STRICT:
        system_parts.append(_TRUTH_STRICT)
    # HYBRID and GENERATIVE → no injection

    # ── formatting + diversity rules ─────────────────────────────────────────
    # Inserted before truth block so the model treats it as a core constraint,
    # not a low-priority hint. Anti-repetition is functional, not cosmetic.
    _variation_rule = (
        "Write in plain text. No markdown tables, no headers, no bold. "
        "Open with the answer itself — the first word of your response is part of the answer. "
        "Vary your sentence openings naturally."
    )
    system_parts.insert(1, _variation_rule)

    system = "\n\n".join(system_parts).strip()
    if system:
        messages.append({"role": "system", "content": system})

    # ── conversation history ──────────────────────────────────────────────────
    _history = _select_relevant_history(ctx.user_message, ctx.conversation_history)
    if _history:
        messages.extend(_history)

    # ── current user message (context injected into user turn) ───────────────
    # Context is injected as raw text BEFORE the user message — no label, no
    # header, no "Context:" prefix. The model reads it as part of the input,
    # not as a named semantic object. Labelling it ("Context (may be partial):")
    # was causing the model to narrate about the context instead of using it
    # silently. Raw injection = invisible grounding. See audit.md §session-4.
    if ctx.retrieved_context:
        user_content = f"{ctx.retrieved_context}\n\n{ctx.user_message}"
    else:
        user_content = ctx.user_message

    messages.append({"role": "user", "content": user_content})

    return messages


def build_system_prompt(persona: str = "", rules: list[str] | None = None) -> str:
    parts: list[str] = []
    if persona:
        parts.append(persona)
    if rules:
        rules_text = "\n".join(f"- {r}" for r in rules)
        parts.append(f"## Rules\n{rules_text}")
    return "\n\n".join(parts)