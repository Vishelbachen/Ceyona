from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Long-Context Role B — pre-synthesis compression step for HEAVY tier.
# Per models.md §26.2 and architecture.md §45.5.
#
# Authority boundary:
#   MUST NOT: influence EPK, select execution tier, alter TruthMode
#   MUST NOT: be substituted for gpt-oss-120b on reasoning tasks
#   MUST NOT: self-activate — called only by _run_heavy() when:
#               complexity == CRITICAL AND input_tokens > 32_000
#   MAY:      compress long input before Heavy Tier execution
#
# Model: qwen/qwen3.6-27b
#   reasoning_effort="none" MANDATORY (models.md §26.2, §27.2)
#   Native context: 262K tokens (sufficient for LC-01/LC-02 test cases)
#   Role B invocation MUST be logged separately from Role A (vision) invocations
#
# Provider: Groq (api.groq.com)
#
# Activation (by _run_heavy only):
#   complexity == Complexity.CRITICAL AND input_tokens > 32_000
#
# Failure mode: non-fatal — caller continues with original input on any error.
#   Heavy Tier (gpt-oss-120b) handles long context natively; Role B is an
#   optimisation, not a requirement for correctness.
#
# Invocation lifecycle (architecture.md §26):
#   _run_heavy → [HERE] → shaper → coordinator → gpt-oss-120b → synthesizer

_LONG_CONTEXT_MODEL = "qwen/qwen3.6-27b"

# Maximum characters of retrieved context to include in the compression prompt.
# Prevents the transformer itself from hitting context limits on extreme inputs.
_MAX_CONTEXT_CHARS = 80_000

# System prompt for Role B — minimal task framing, no persona (models.md §26.2).
_SYSTEM_PROMPT = (
    "You are a text compression assistant. "
    "Your only task: given a long conversation context and user request, "
    "produce a compact, lossless summary that preserves all facts, "
    "numbers, names, constraints, and logical structure needed to answer "
    "the request. Output only the compressed text — no preamble, no explanation."
)


@dataclass(frozen=True)
class LongContextResult:
    compressed_text: str
    model_used: str
    success: bool
    error: str = ""


async def transform(
    user_message: str,
    retrieved_context: str = "",
    conversation_history: list[dict] | None = None,
    input_tokens: int = 0,
) -> LongContextResult:
    """
    Compress a long-context request for downstream Heavy Tier execution.

    Called by _run_heavy() only — never self-activates.
    Returns LongContextResult(success=False) on any error; caller continues
    with original input (non-fatal failure mode).

    Logging: uses "long_context_role_b" tag to distinguish from Role A (vision)
    invocations of the same qwen/qwen3.6-27b model (models.md §26.2 requirement).
    """
    if not user_message.strip():
        return LongContextResult(
            compressed_text="",
            model_used=_LONG_CONTEXT_MODEL,
            success=False,
            error="empty user_message",
        )

    try:
        import httpx
        from app.settings import settings

        # Build compression prompt — fold context + history + user message
        parts: list[str] = []

        if conversation_history:
            history_text = "\n".join(
                f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
                for m in conversation_history[-10:]  # last 10 turns sufficient
                if isinstance(m.get("content"), str)
            )
            if history_text:
                parts.append(f"[CONVERSATION HISTORY]\n{history_text}")

        if retrieved_context:
            ctx_truncated = retrieved_context[:_MAX_CONTEXT_CHARS]
            parts.append(f"[RETRIEVED CONTEXT]\n{ctx_truncated}")

        parts.append(f"[USER REQUEST]\n{user_message}")

        compression_input = "\n\n".join(parts)

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": compression_input},
        ]

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _LONG_CONTEXT_MODEL,
                    "messages": messages,
                    # reasoning_effort="none" MANDATORY — models.md §26.2, §27.2
                    "reasoning_effort": "none",
                    "temperature": 0.3,   # low temperature: compression is deterministic
                    "top_p": 0.80,
                    # top_k omitted — not supported by Groq OpenAI-compatible API
                    "presence_penalty": 0.0,
                    "max_tokens": 4096,
                },
            )

        if response.status_code != 200:
            logger.warning(
                "Long-Context Role B API error",
                extra={
                    "role": "long_context_role_b",
                    "status": response.status_code,
                    "model": _LONG_CONTEXT_MODEL,
                },
            )
            return LongContextResult(
                compressed_text="",
                model_used=_LONG_CONTEXT_MODEL,
                success=False,
                error=f"API status {response.status_code}: {response.text[:200]}",
            )

        body = response.json()
        compressed = body["choices"][0]["message"]["content"].strip()

        if not compressed:
            return LongContextResult(
                compressed_text="",
                model_used=_LONG_CONTEXT_MODEL,
                success=False,
                error="empty compression result",
            )

        logger.info(
            "Long-Context Role B: compression complete",
            extra={
                "role": "long_context_role_b",   # distinguishes from Role A vision logs
                "model": _LONG_CONTEXT_MODEL,
                "input_tokens": input_tokens,
                "output_chars": len(compressed),
                "compression_ratio": round(len(compression_input) / max(len(compressed), 1), 2),
            },
        )

        return LongContextResult(
            compressed_text=compressed,
            model_used=_LONG_CONTEXT_MODEL,
            success=True,
        )

    except Exception as exc:
        logger.warning(
            "Long-Context Role B exception — non-fatal",
            extra={
                "role": "long_context_role_b",
                "error": str(exc),
                "model": _LONG_CONTEXT_MODEL,
            },
        )
        return LongContextResult(
            compressed_text="",
            model_used=_LONG_CONTEXT_MODEL,
            success=False,
            error=str(exc),
        )