from dataclasses import dataclass

from contracts.shared_types import TruthMode

# ─── TRUTH ENFORCEMENT PROMPTS ───────────────────────────────────────────────

_TRUTH_STRICT = """
CRITICAL INSTRUCTIONS — these override everything else:
1. You MUST use ONLY the information provided in the ## CONTEXT section below.
2. If the context contains the answer — use it directly and completely.
3. If the context does NOT contain enough information — reply: "I could not find reliable data on this topic."
4. You are FORBIDDEN from using your training knowledge for facts, numbers, dates, names, or current events.
5. Never say "my database is outdated" — that is not your role. Just use the context or say not found.
6. ALWAYS reply in the SAME language the user wrote in. Never mix languages. Never use English words in Russian sentences.
""".strip()

_TRUTH_HYBRID = """
INSTRUCTIONS:
1. The ## CONTEXT section below contains real, current data retrieved for this request — USE IT.
2. Base your answer primarily on the context. You may add general knowledge only to clarify or explain.
3. Never invent facts, statistics, dates, names, or prices not present in the context.
4. If unsure about something — say so explicitly instead of guessing.
5. ALWAYS reply in the SAME language the user wrote in. Never mix languages. Never use English words in Russian sentences.
""".strip()


@dataclass(frozen=True)
class PromptContext:
    user_message: str
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    truth_mode: TruthMode = TruthMode.HYBRID


def build_messages(ctx: PromptContext) -> list[dict]:
    messages: list[dict] = []

    system_parts: list[str] = []

    # ── language instruction (always first) ──────────────
    system_parts.append(
        f"You MUST reply in the same language the user writes in. "
        f"Never mix languages. Never use English words inside non-English sentences."
    )

    if ctx.system_prompt:
        system_parts.append(ctx.system_prompt)

    if ctx.truth_mode == TruthMode.STRICT:
        system_parts.append(_TRUTH_STRICT)
    elif ctx.truth_mode == TruthMode.HYBRID:
        system_parts.append(_TRUTH_HYBRID)

    if ctx.retrieved_context:
        system_parts.append(f"## CONTEXT\n{ctx.retrieved_context}")

    system = "\n\n".join(system_parts).strip()
    if system:
        messages.append({"role": "system", "content": system})

    if ctx.conversation_history:
        messages.extend(ctx.conversation_history)

    messages.append({"role": "user", "content": ctx.user_message})

    return messages

    # ── base system prompt ───────────────────────────────
    system_parts: list[str] = []

    if ctx.system_prompt:
        system_parts.append(ctx.system_prompt)

    # ── truth enforcement injection ──────────────────────
    if ctx.truth_mode == TruthMode.STRICT:
        system_parts.append(_TRUTH_STRICT)
    elif ctx.truth_mode == TruthMode.HYBRID:
        system_parts.append(_TRUTH_HYBRID)
    # GENERATIVE → no injection

    # ── retrieved context ────────────────────────────────
    if ctx.retrieved_context:
        system_parts.append(
            f"## CONTEXT\n{ctx.retrieved_context}"
        )

    system = "\n\n".join(system_parts).strip()
    if system:
        messages.append({"role": "system", "content": system})

    # ── conversation history ─────────────────────────────
    if ctx.conversation_history:
        messages.extend(ctx.conversation_history)

    # ── current user message ─────────────────────────────
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