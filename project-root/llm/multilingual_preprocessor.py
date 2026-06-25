from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Multilingual Normalization step — runs BEFORE EPK, per architecture.md §4.
#
# Responsibilities:
#   - Detect script/language of input
#   - For Arabic: normalize via allam-2-7b (one call, three contexts per models.md)
#   - For all other non-Latin: normalize via qwen/qwen3.6-27b (replaces llama-3.3-70b-versatile,
#     deprecated Aug 16, 2026 — models.md §23, §28)
#   - For Latin-script languages: pass through unchanged (no LLM call needed)
#
# Position in lifecycle:
#   User Input → Safety Gate → Feature Extraction → [HERE] → EPK → ...
#
# Authority boundary:
#   MUST NOT: influence EPK, select models, mutate routing, alter TruthMode
#   MAY: normalize text encoding, fix transliteration artifacts,
#        standardize punctuation for downstream processing
#
# Does NOT translate — it normalizes within the same language.
# Translation is a cognition concern, not a preprocessing concern.

# ─── SCRIPT DETECTION ────────────────────────────────────────────────────────

_ARABIC_RANGE = (0x0600, 0x06FF)   # Arabic
_ARABIC_EXT = (0xFB50, 0xFDFF)     # Arabic Presentation Forms-A
_ARABIC_EXT2 = (0xFE70, 0xFEFF)    # Arabic Presentation Forms-B

_NON_LATIN_RANGES: list[tuple[int, int]] = [
    (0x0400, 0x04FF),   # Cyrillic
    (0x0370, 0x03FF),   # Greek
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0x0900, 0x097F),   # Devanagari
    (0x10D0, 0x10FF),   # Georgian
    (0x0600, 0x06FF),   # Arabic (also checked separately)
    (0x0590, 0x05FF),   # Hebrew
    (0x0E00, 0x0E7F),   # Thai
]

_MAX_SAMPLE = 240
_TIMEOUT_SECONDS = 20.0


def _char_in_range(char: str, ranges: list[tuple[int, int]]) -> bool:
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in ranges)


def _is_arabic_script(text: str) -> bool:
    """Return True if text contains significant Arabic script content."""
    sample = text[:_MAX_SAMPLE]
    arabic_chars = sum(
        1 for c in sample
        if (_ARABIC_RANGE[0] <= ord(c) <= _ARABIC_RANGE[1])
        or (_ARABIC_EXT[0] <= ord(c) <= _ARABIC_EXT[1])
        or (_ARABIC_EXT2[0] <= ord(c) <= _ARABIC_EXT2[1])
    )
    return arabic_chars / max(len(sample), 1) > 0.15


def _needs_normalization(text: str) -> bool:
    """Return True if text contains non-Latin script characters."""
    sample = text[:_MAX_SAMPLE]
    non_latin = sum(1 for c in sample if _char_in_range(c, _NON_LATIN_RANGES))
    return non_latin / max(len(sample), 1) > 0.10


def _clean_normalized_text(text: str) -> str:
    cleaned = text.strip()

    # Strip <think>...</think> blocks that qwen may emit even with reasoning_effort="none"
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()

    if len(cleaned) >= 2:
        fence_pairs = (("```", "```"), ("~~~", "~~~"))
        for open_fence, close_fence in fence_pairs:
            if cleaned.startswith(open_fence) and cleaned.endswith(close_fence):
                cleaned = cleaned[len(open_fence) : -len(close_fence)].strip()
                break

    # Remove wrapping quotes that models sometimes add around normalized text.
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'", "«", "»", "“", "”"}:
        cleaned = cleaned[1:-1].strip()

    return cleaned


def _script_ratio(text: str) -> float:
    sample = text[:_MAX_SAMPLE]
    if not sample:
        return 0.0
    non_latin = sum(1 for c in sample if _char_in_range(c, _NON_LATIN_RANGES))
    return non_latin / len(sample)


# ─── CONTRACTS ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PreprocessorInput:
    text: str
    lang: str          # detected language code (e.g. "ar", "ru", "ja")


@dataclass(frozen=True)
class PreprocessorResult:
    text: str          # normalized text (may be identical to input)
    model_used: str    # model name or "passthrough"
    was_normalized: bool


# ─── NORMALIZATION PROMPTS ────────────────────────────────────────────────────

_ARABIC_SYSTEM = (
    "أنت محوّل نصوص عربية. مهمتك الوحيدة هي تطبيع النص المُدخل: "
    "توحيد علامات الترقيم، تصحيح التشكيل الزائد، "
    "وإزالة الأحرف غير المعيارية. "
    "أعد النص المُطبَّع فقط، بدون أي تعليقات أو إضافات."
)

_OTHER_SYSTEM = (
    "You are a text normalizer. Your only task is to normalize the input text: "
    "standardize punctuation, fix encoding artifacts, remove non-standard characters. "
    "Return only the normalized text — no commentary, no additions, no translation."
)


# ─── CORE ─────────────────────────────────────────────────────────────────────

async def preprocess(inp: PreprocessorInput) -> PreprocessorResult:
    """
    Normalize multilingual input before EPK and intent classification.

    Decision tree:
      1. Latin-dominant script → passthrough (no LLM call)
      2. Arabic script → allam-2-7b normalization
      3. Other non-Latin script → qwen/qwen3.6-27b normalization (models.md §23)

    Never raises — returns original text on any failure.
    Never translates — only normalizes within the same language.
    """
    if not inp.text or not inp.text.strip():
        return PreprocessorResult(
            text=inp.text,
            model_used="passthrough",
            was_normalized=False,
        )

    # Fast path: Latin-dominant text needs no LLM normalization.
    if not _needs_normalization(inp.text):
        return PreprocessorResult(
            text=inp.text,
            model_used="passthrough",
            was_normalized=False,
        )

    is_arabic = _is_arabic_script(inp.text) or inp.lang == "ar"

    from llm.groq_client import groq_client
    from llm.model_router import MULTILINGUAL_ARABIC_MODEL, MULTILINGUAL_OTHER_MODEL

    model = MULTILINGUAL_ARABIC_MODEL if is_arabic else MULTILINGUAL_OTHER_MODEL
    system = _ARABIC_SYSTEM if is_arabic else _OTHER_SYSTEM

    try:
        extra_kwargs: dict = {}
        if model == "qwen/qwen3.6-27b":
            extra_kwargs["reasoning_effort"] = "none"  # mandatory per models.md §27.2

        response = await asyncio.wait_for(
            groq_client.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": inp.text},
                ],
                max_tokens=min(256, max(64, len(inp.text) // 2 + 64)),
                temperature=0.1,
                **extra_kwargs,
            ),
            timeout=_TIMEOUT_SECONDS,
        )

        normalized = _clean_normalized_text(response.text)
        if not normalized:
            logger.warning(
                "multilingual_preprocessor: empty response — using original",
                extra={"model": model, "lang": inp.lang},
            )
            return PreprocessorResult(
                text=inp.text,
                model_used=model,
                was_normalized=False,
            )

        # Guard against accidental translation or script collapse.
        if _script_ratio(inp.text) > 0.10 and _script_ratio(normalized) < 0.05:
            logger.warning(
                "multilingual_preprocessor: output lost original script — using original",
                extra={"model": model, "lang": inp.lang},
            )
            return PreprocessorResult(
                text=inp.text,
                model_used=model,
                was_normalized=False,
            )

        logger.info(
            "multilingual_preprocessor: normalized",
            extra={"model": model, "lang": inp.lang, "script": "arabic" if is_arabic else "other"},
        )
        return PreprocessorResult(
            text=normalized,
            model_used=model,
            was_normalized=True,
        )

    except Exception as exc:
        logger.warning(
            "multilingual_preprocessor: failed — using original text",
            extra={"model": model, "lang": inp.lang, "error": str(exc)},
        )
        return PreprocessorResult(
            text=inp.text,
            model_used="passthrough",
            was_normalized=False,
        )