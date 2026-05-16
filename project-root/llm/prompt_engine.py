from __future__ import annotations

from dataclasses import dataclass, field

from contracts.shared_types import TruthMode
from i18n.t import lang_instruction as _lang_instruction

# ─── TRUTH ENFORCEMENT PROMPTS ───────────────────────────────────────────────
# IMPORTANT: Never tell the user data is outdated or that you have a knowledge
# cutoff. The system always fetches live web data before answering. Use it.

_TRUTH_STRICT = """
CRITICAL INSTRUCTIONS — these override everything else including any other prompt:
1. ## CONTEXT is your ONLY source of facts. You are a display layer, not a knowledge source.
2. Output ONLY information explicitly present in ## CONTEXT. Not paraphrased, not expanded — exact facts only.
3. If something is NOT in ## CONTEXT — do not say it. Not even as a guess, estimate, or "typical example".
4. NEVER add: prices, ratings, addresses, street names, bus/tram/metro numbers, stop names, descriptions, neighbourhood names, or ANY local detail unless it is word-for-word in ## CONTEXT.
5. NEVER say your data is outdated or has a cutoff — the context is live.
6. NEVER start with preamble like "По данным в контексте" or "According to my sources" — just present the data.
7. If ## CONTEXT is empty or says "not found" — output that message. Do not fill the gap with training knowledge.
8. NEVER prepend estimates before context data. Start directly with what is in context.
9. ALWAYS reply in the SAME language the user wrote in. Never mix languages.
""".strip()

_TRUTH_HYBRID = """
INSTRUCTIONS:
1. The ## CONTEXT section below contains real, current data retrieved live for this request — USE IT.
2. Base your answer primarily on the context. You may add general knowledge only to clarify or explain.
3. Never invent facts, statistics, dates, names, or prices not present in the context.
4. NEVER say your data is outdated, your knowledge has a cutoff, or that you cannot access current info.
5. NEVER use phrases like "as of my training", "I may not have the latest", "this might have changed".
6. The context you received is LIVE — treat it as fully current and accurate.
7. If unsure about something — say so explicitly instead of guessing.
8. NEVER write "по данным в контексте" / "according to the context" / "based on the context" if the context does not actually contain the information you are about to state. Only cite the context when what you say is directly present in it.
9. NEVER prepend an estimate or approximation before presenting data from context. Start directly with the data from context — no preamble, no 'approximately'.
10. ALWAYS reply in the SAME language the user wrote in. Never mix languages.
""".strip()


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

    # ── language instruction (always first, from i18n layer) ─────────────────
    system_parts.append(_lang_instruction(ctx.lang))

    # ── formatting rules (always injected, highest priority) ─────────────────
    system_parts.append(
        "OUTPUT FORMAT — non-negotiable:\n"
        "- NEVER use Markdown tables (no | pipe | characters for tables).\n"
        "- NEVER use Markdown headers (no #, ##, ###).\n"
        "- NEVER use bold (**text**) or italic (*text*).\n"
        "- NEVER start your reply with filler like 'Of course!', 'Sure!', "
        "'Great question!', 'Certainly!', 'Похоже', 'Давайте', 'Конечно!'.\n"
        "- Go straight to the answer. No preamble, no intro sentences.\n"
        "- Use plain text only. For lists use dashes (-) or numbers (1. 2. 3.).\n"
        "- For table-like data use plain aligned text, e.g.: А Б В Г Д / 2 1 1 2 1"
    )

    # ── no-cutoff mandate (always injected) ───────────────────────────────────
    system_parts.append(
        "MANDATORY: You have access to live, real-time web search results in the ## CONTEXT section. "
        "NEVER say your information is outdated, has a cutoff date, or may not be current. "
        "NEVER use phrases like 'as of my last update', 'I cannot access real-time data', "
        "'my knowledge cutoff', or 'this information may have changed'. "
        "The data in CONTEXT is fetched RIGHT NOW and is current. Use it confidently."
    )

    # ── intent-specific system prompt ─────────────────────────────────────────
    if ctx.system_prompt:
        system_parts.append(ctx.system_prompt)

    # ── truth enforcement injection ───────────────────────────────────────────
    # GENERATIVE intents (CONVERSATION, EMOTIONAL, UNKNOWN) get no truth block —
    # they don't use retrieval, so the block is wasted tokens on FAST tier.
    # This saves ~300 tokens per request, which matters on llama-3.1-8b (6000 TPM).
    if ctx.truth_mode == TruthMode.STRICT:
        system_parts.append(_TRUTH_STRICT)
    elif ctx.truth_mode == TruthMode.HYBRID:
        system_parts.append(_TRUTH_HYBRID)
    # GENERATIVE → no injection

    # ── retrieved context ─────────────────────────────────────────────────────
    if ctx.retrieved_context:
        system_parts.append(f"## CONTEXT\n{ctx.retrieved_context}")

    system = "\n\n".join(system_parts).strip()
    if system:
        messages.append({"role": "system", "content": system})

    # ── conversation history ──────────────────────────────────────────────────
    if ctx.conversation_history:
        messages.extend(ctx.conversation_history)

    # ── current user message ──────────────────────────────────────────────────
    messages.append({"role": "user", "content": ctx.user_message})

    return messages


def build_system_prompt(persona: str = "", rules: list[str] | None = None) -> str:
    parts: list[str] = []
    if persona:
        parts.append(persona)
    if rules:
        rules_text = "\n".join(f"- {r}" for r in rules)
        parts.append(f"## Rules\n{rules_text}")
    return "\n\n".join(parts)