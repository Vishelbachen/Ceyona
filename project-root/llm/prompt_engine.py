from dataclasses import dataclass


@dataclass(frozen=True)
class PromptContext:
    user_message: str
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None


def build_messages(ctx: PromptContext) -> list[dict]:
    """
    Assemble messages array for LLM from prompt context.
    Format: [system, ...history, user]
    """
    messages: list[dict] = []

    # ── system prompt ────────────────────────────────────
    system = ctx.system_prompt
    if ctx.retrieved_context:
        system = (
            f"{system}\n\n"
            f"## Relevant context\n{ctx.retrieved_context}"
        ).strip()

    if system:
        messages.append({"role": "system", "content": system})

    # ── conversation history ─────────────────────────────
    if ctx.conversation_history:
        messages.extend(ctx.conversation_history)

    # ── current user message ─────────────────────────────
    messages.append({"role": "user", "content": ctx.user_message})

    return messages


def build_system_prompt(persona: str = "", rules: list[str] | None = None) -> str:
    """
    Build a system prompt string from persona and rules.
    Optional helper — use when you need structured system prompts.
    """
    parts: list[str] = []

    if persona:
        parts.append(persona)

    if rules:
        rules_text = "\n".join(f"- {r}" for r in rules)
        parts.append(f"## Rules\n{rules_text}")

    return "\n\n".join(parts)