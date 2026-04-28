from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier


# ─── INPUT / OUTPUT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: Intent
    tier: Tier
    denied: bool = False
    deny_reason: str = ""


@dataclass(frozen=True)
class SynthesisResult:
    text: str               # final user-facing text
    truncated: bool = False


# ─── TELEGRAM MESSAGE LIMITS ─────────────────────────────────────────────────

_TELEGRAM_MAX_CHARS = 4096
_TRUNCATION_SUFFIX = "\n\n_...ответ сокращён_"


# ─── DENY MESSAGES ───────────────────────────────────────────────────────────

_DENY_MESSAGES: dict[str, str] = {
    "insufficient_balance": (
        "⚠️ *Недостаточно средств.*\n"
        "Пополните баланс, чтобы продолжить."
    ),
    "empty_message": "",        # silent — don't reply to empty messages
    "no_user_id": "",
    "default": "⚠️ Запрос не может быть выполнен.",
}


# ─── FORMATTING RULES PER INTENT ─────────────────────────────────────────────

def _format(text: str, intent: Intent) -> str:
    """Apply light formatting based on intent. Never changes content."""
    text = text.strip()

    # Code blocks: ensure language tag present if ``` used
    if intent == Intent.CODE:
        return text     # LLM already formats code

    # Conversation: no markdown
    if intent == Intent.CONVERSATION:
        return text

    return text


def _truncate(text: str) -> tuple[str, bool]:
    """Truncate to Telegram message limit if needed."""
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False

    cut = _TELEGRAM_MAX_CHARS - len(_TRUNCATION_SUFFIX)
    return text[:cut] + _TRUNCATION_SUFFIX, True


# ─── MAIN SYNTHESIZER ────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into final user-facing text.
    Pure function. No I/O. No state.
    """
    # ── denied request ───────────────────────────────────
    if inp.denied:
        msg = _DENY_MESSAGES.get(inp.deny_reason, _DENY_MESSAGES["default"])
        return SynthesisResult(text=msg, truncated=False)

    # ── empty LLM response ───────────────────────────────
    if not inp.raw_text or not inp.raw_text.strip():
        return SynthesisResult(
            text="⚠️ Не удалось получить ответ. Попробуйте ещё раз.",
            truncated=False,
        )

    # ── format ───────────────────────────────────────────
    formatted = _format(inp.raw_text, inp.intent)

    # ── truncate ─────────────────────────────────────────
    final, truncated = _truncate(formatted)

    return SynthesisResult(text=final, truncated=truncated)