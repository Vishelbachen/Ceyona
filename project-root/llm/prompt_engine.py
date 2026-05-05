from dataclasses import dataclass

from contracts.shared_types import TruthMode

# ─── TRUTH ENFORCEMENT PROMPTS ───────────────────────────────────────────────

_TRUTH_STRICT = """
CRITICAL RULES — follow without exception:
- Answer ONLY using information from the CONTEXT section below.
- If the context does not contain enough information to answer — say exactly:
  "I could not find reliable information on this."
- Do NOT invent, assume, or extrapolate any facts.
- Do NOT use your training knowledge for factual claims.
- Do NOT make up names, dates, numbers, events, or statistics.
- ALWAYS reply in the SAME language the user wrote in. Never mix languages.
""".strip()

_TRUTH_HYBRID = """
RULES:
- Prioritize information from the CONTEXT section below.
- You may use your general knowledge only to explain or clarify context data.
- Do NOT invent specific facts, numbers, dates, or names not present in context.
- If unsure — say so explicitly.
- ALWAYS reply in the SAME language the user wrote in. Never mix languages.
""".strip()


@dataclass(frozen=True)
class PromptContext:
    user_message: str
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    truth_mode: TruthMode = TruthMode.HYBRID


def build_messages(ctx: PromptContext) -> list[dict]:
    """
    Assemble messages array for LLM from prompt context.
    Format: [system, ...history, user]
    Injects truth enforcement rules based on TruthMode.
    """
    messages: list[dict] = []

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