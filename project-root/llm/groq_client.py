from __future__ import annotations

from dataclasses import dataclass

from groq import AsyncGroq

from app.settings import settings


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


# ── Context window limits per model (input tokens) ───────────────────────────
# Conservative: actual limits minus output budget minus safety margin.
# Source: Groq model cards (May 2026).
_CONTEXT_CHAR_LIMITS: dict[str, int] = {
    "llama-3.1-8b-instant":           60_000,   # 128K ctx → ~60K chars safe input
    "llama-3.3-70b-versatile":        60_000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 200_000,  # 512K ctx
    "qwen/qwen3-32b":                 60_000,
    "openai/gpt-oss-20b":             60_000,
    "openai/gpt-oss-120b":            60_000,
    "groq/compound-mini":             60_000,
    "groq/compound":                  60_000,
}
_DEFAULT_CHAR_LIMIT = 50_000  # fallback for unknown models

# Safety Gate — short inputs only (guard models are classifiers, not generators)
_CONTEXT_CHAR_LIMITS["meta-llama/llama-prompt-guard-2-22m"] = 4_000
_CONTEXT_CHAR_LIMITS["meta-llama/llama-prompt-guard-2-86m"] = 8_000
_CONTEXT_CHAR_LIMITS["openai/gpt-oss-safeguard-20b"]        = 16_000

# Speech models — no text context limit (audio input, not token-based)
# Listed here for registry completeness; they use separate audio/char billing.
_CONTEXT_CHAR_LIMITS["whisper-large-v3"]                = 0  # audio input
_CONTEXT_CHAR_LIMITS["whisper-large-v3-turbo"]          = 0  # audio input
_CONTEXT_CHAR_LIMITS["canopylabs/orpheus-v1-english"]   = 50_000  # TTS text input
_CONTEXT_CHAR_LIMITS["canopylabs/orpheus-arabic-saudi"] = 50_000  # TTS text input

# Multilingual normalization
_CONTEXT_CHAR_LIMITS["allam-2-7b"] = 20_000


def _truncate_messages(messages: list[dict], char_limit: int) -> list[dict]:
    """
    Truncate messages to fit within char_limit.

    Strategy:
    1. Always keep system message (index 0 if role=system).
    2. Always keep the last user message.
    3. Drop oldest non-system, non-last messages from the middle.
    4. If the last user message itself exceeds the limit, truncate its content.
    """
    if not messages:
        return messages

    # Fast path: already fits
    total = sum(len(str(m.get("content") or "")) for m in messages)
    if total <= char_limit:
        return messages

    system_msgs  = [m for m in messages if m.get("role") == "system"]
    other_msgs   = [m for m in messages if m.get("role") != "system"]

    if not other_msgs:
        # Only system — truncate it
        s = system_msgs[0]
        content = str(s.get("content") or "")
        return [{**s, "content": content[:char_limit]}]

    last_msg    = other_msgs[-1]
    middle_msgs = other_msgs[:-1]

    # Budget: char_limit minus system and last message
    system_chars = sum(len(str(m.get("content") or "")) for m in system_msgs)
    last_chars   = len(str(last_msg.get("content") or ""))
    budget       = char_limit - system_chars - last_chars

    # If even without middle we exceed, truncate last message content
    if budget < 0:
        safe_last_len = max(500, char_limit - system_chars)
        content = str(last_msg.get("content") or "")
        last_msg = {**last_msg, "content": content[:safe_last_len]}
        return system_msgs + [last_msg]

    # Fill middle messages from newest to oldest until budget exhausted
    kept_middle: list[dict] = []
    used = 0
    for msg in reversed(middle_msgs):
        msg_len = len(str(msg.get("content") or ""))
        if used + msg_len > budget:
            break
        kept_middle.insert(0, msg)
        used += msg_len

    return system_msgs + kept_middle + [last_msg]


class GroqClient:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)

    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 1200,
        temperature: float = 0.7,
        **extra_params,
    ) -> LLMResponse:
        # Truncate input to prevent 413 Payload Too Large
        char_limit = _CONTEXT_CHAR_LIMITS.get(model, _DEFAULT_CHAR_LIMIT)
        messages = _truncate_messages(messages, char_limit)

        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **extra_params,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=response.model,
        )


# Singleton
groq_client = GroqClient()