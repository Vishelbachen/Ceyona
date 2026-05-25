from __future__ import annotations

from dataclasses import dataclass

from contracts.shared_types import TruthMode
from i18n.t import lang_instruction as _lang_instruction

# ─── TRUTH ENFORCEMENT PROMPTS ───────────────────────────────────────────────
# STRICT: for intents where only retrieved data is valid (maps, poi, routes).
# HYBRID: for intents where context grounds the answer but LLM can clarify.
# GENERATIVE: no truth block — conversation/emotional/creative don't use retrieval.

_TRUTH_STRICT = (
    "The context below contains the only facts available for this request. "
    "Output only what is explicitly present in it — do not add, estimate, or infer. "
    "If the context is empty or incomplete — say so directly instead of filling the gap."
)

_TRUTH_HYBRID = (
    "Context below may be partial or imperfect — use it as your primary source, "
    "but apply judgment. If context and common sense conflict, note the discrepancy. "
    "If you are unsure about something, say so instead of guessing."
)


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

    # ── truth enforcement (only when retrieval is involved) ───────────────────
    # GENERATIVE intents (CONVERSATION, EMOTIONAL, CREATIVE, UNKNOWN) get no
    # truth block — they don't use retrieval.
    if ctx.truth_mode == TruthMode.STRICT:
        system_parts.append(_TRUTH_STRICT)
    elif ctx.truth_mode == TruthMode.HYBRID:
        system_parts.append(_TRUTH_HYBRID)
    # GENERATIVE → no injection

    # ── formatting + diversity rules ─────────────────────────────────────────
    # Inserted before truth block so the model treats it as a core constraint,
    # not a low-priority hint. Anti-repetition is functional, not cosmetic.
    #
    # History-aware variation: if conversation history contains recent assistant
    # turns, extract their opening phrases and inject them explicitly so the model
    # knows what to avoid. This makes the variation instruction actionable rather
    # than abstract — the model can only vary what it can see.
    _recent_openings: list[str] = []
    if ctx.conversation_history:
        for turn in ctx.conversation_history[-6:]:  # last 3 pairs at most
            if turn.get("role") == "assistant":
                content = turn.get("content") or ""
                opening = content.strip().split("\n")[0][:80].strip()
                if opening:
                    _recent_openings.append(opening)

    if _recent_openings:
        _openings_block = "; ".join(f'"{o}"' for o in _recent_openings[-3:])
        _variation_rule = (
            "Write in plain text. No markdown tables, no headers, no bold. "
            "Go straight to the answer — no filler openers. "
            f"Your recent responses started with: {_openings_block}. "
            "Do NOT start this response the same way. Vary your opening naturally."
        )
    else:
        _variation_rule = (
            "Write in plain text. No markdown tables, no headers, no bold. "
            "Go straight to the answer — no filler openers. "
            "Vary your sentence openings naturally."
        )
    system_parts.insert(1, _variation_rule)

    system = "\n\n".join(system_parts).strip()
    if system:
        messages.append({"role": "system", "content": system})

    # ── conversation history ──────────────────────────────────────────────────
    if ctx.conversation_history:
        messages.extend(ctx.conversation_history)

    # ── current user message (context injected into user turn) ───────────────
    # Context goes into the USER turn, not system — forces model to read it
    # immediately before generating, preventing "forgetting" on small models.
    if ctx.retrieved_context:
        user_content = (
            f"Context (may be partial):\n{ctx.retrieved_context}\n\n"
            f"{ctx.user_message}"
        )
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