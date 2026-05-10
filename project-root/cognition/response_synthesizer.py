from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier
from i18n.strings import t as _t, normalize_lang, _SILENT_KEYS

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_CHARS = 4096


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def get_system_message(key: str, lang: str) -> str:
    return _t(key, lang) or "⚠️ An error occurred."


def format_balance_message(balance: float, lang: str) -> str:
    return _t("balance_display", lang, amount=f"{balance:.2f}")


# ─── I/O CONTRACTS ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: "Intent | None"
    tier: Tier
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    truncated: bool = False


# ─── INTERNAL PIPELINE ────────────────────────────────────────────────────────

def _assemble(raw: str) -> str:
    return raw


def _structure(text: str, intent: "Intent | None") -> str:
    return text


def _normalize_for_telegram(text: str) -> str:
    """Strip LaTeX math delimiters and Markdown formatting that Telegram cannot render."""
    import re
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text


def _format(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _apply_correction(text: str) -> str:
    try:
        from meta.correction import apply
        corrected = apply(text)
        return corrected if corrected and corrected.strip() else text
    except Exception:
        return text


def _truncate(text: str, lang: str) -> tuple[str, bool]:
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    suffix = _t("truncation_suffix", lang)
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


def _finalize(text: str, lang: str) -> tuple[str, bool]:
    return _truncate(text, lang)


# ─── MAIN SYNTHESIZER ─────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into the final user-facing message.

    Pipeline:
      1. assemble     — accept raw text
      2. structure    — intent-aware shaping
      3. normalize    — strip LaTeX/Markdown Telegram can't render
      4. format       — whitespace normalisation
      5. correction   — meta/correction
      6. finalize     — truncate to Telegram limit
    """
    lang = normalize_lang(inp.lang)

    # ── DENY path ─────────────────────────────────────────────────────────────
    if inp.denied:
        # Use deny_reason as key if it's a known silent key, else look up message
        if inp.deny_reason in _SILENT_KEYS:
            return SynthesisResult(text="")
        # Try deny_reason as a string key; fall back to default_deny
        msg = _t(inp.deny_reason, lang)
        if not msg:
            msg = _t("default_deny", lang)
        return SynthesisResult(text=msg)

    # ── no LLM response ───────────────────────────────────────────────────────
    if not inp.raw_text or not inp.raw_text.strip():
        from cognition.intent_engine import Intent as _Intent
        if inp.intent == _Intent.EMOTIONAL:
            return SynthesisResult(text=_t("emotional_fallback", lang))
        return SynthesisResult(text=_t("no_response", lang))

    # ── normal pipeline ───────────────────────────────────────────────────────
    text = _assemble(inp.raw_text)
    text = _normalize_for_telegram(text)
    text = _structure(text, inp.intent)
    text = _format(text)
    text = _apply_correction(text)
    text, truncated = _finalize(text, lang)

    return SynthesisResult(text=text, truncated=truncated)
