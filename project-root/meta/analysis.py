from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# ─── HINT TYPES ───────────────────────────────────────────────────────────────

class HintType(str, Enum):
    # Structural signals
    HAS_CODE_BLOCK   = "has_code_block"
    HAS_JSON         = "has_json"
    HAS_MATH         = "has_math"
    HAS_LIST         = "has_list"
    HAS_URL          = "has_url"

    # Length / density signals
    IS_SHORT         = "is_short"         # ≤ 20 words
    IS_LONG          = "is_long"          # ≥ 200 words
    IS_MULTIPART     = "is_multipart"     # contains numbered parts or bullet points

    # Language signals
    IS_MULTILINGUAL  = "is_multilingual"  # detects mixed scripts
    SCRIPT_ARABIC    = "script_arabic"
    SCRIPT_CJK       = "script_cjk"
    SCRIPT_CYRILLIC  = "script_cyrillic"
    SCRIPT_LATIN     = "script_latin"

    # Tone signals (lightweight heuristics only, not semantic)
    LIKELY_QUESTION  = "likely_question"
    LIKELY_COMMAND   = "likely_command"


@dataclass(frozen=True)
class AnalysisHint:
    hint: HintType
    value: bool | str | float    # depends on hint type
    confidence: float            # 0.0 – 1.0, purely structural


@dataclass(frozen=True)
class AnalysisReport:
    """
    Non-binding structural analysis of the input text.
    Passed as context hints to intent_engine — intent_engine may ignore them.
    Zero execution authority.
    """
    hints: list[AnalysisHint]
    word_count: int
    char_count: int
    dominant_script: str         # "latin" | "cyrillic" | "arabic" | "cjk" | "mixed"
    lightweight: bool = False    # True when produced in DEGRADED_MODE

    def has(self, hint: HintType) -> bool:
        return any(h.hint == hint and h.value for h in self.hints)

    def get(self, hint: HintType) -> AnalysisHint | None:
        return next((h for h in self.hints if h.hint == hint), None)


# ─── REGEX PATTERNS (compiled once at import) ─────────────────────────────────

_RE_CODE_BLOCK   = re.compile(r"```[\s\S]*?```|`[^`\n]+`")
_RE_JSON         = re.compile(r"\{[\s\S]{2,}\}|\[[\s\S]{2,}\]")
_RE_MATH         = re.compile(r"[=∑∫√²³π÷×±≈≠≤≥]|\b\d+[\+\-\*/]\d+")
_RE_URL          = re.compile(r"https?://\S+|www\.\S+")
_RE_LIST_ITEM    = re.compile(r"^\s*[-•*]\s|\b\d+[.)]\s", re.MULTILINE)
_RE_NUMBERED_Q   = re.compile(r"^\s*\d+[.)]\s.+", re.MULTILINE)

# Script detection ranges
_RE_ARABIC    = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_RE_CJK       = re.compile(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF]")
_RE_CYRILLIC  = re.compile(r"[\u0400-\u04FF]")
_RE_LATIN     = re.compile(r"[A-Za-z]")


# ─── SCRIPT DETECTION ─────────────────────────────────────────────────────────

def _detect_scripts(text: str) -> dict[str, int]:
    return {
        "arabic":   len(_RE_ARABIC.findall(text)),
        "cjk":      len(_RE_CJK.findall(text)),
        "cyrillic": len(_RE_CYRILLIC.findall(text)),
        "latin":    len(_RE_LATIN.findall(text)),
    }


def _dominant_script(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "latin"

    dominant = max(counts, key=counts.get)
    dominant_ratio = counts[dominant] / total

    # If dominant script covers < 70% → mixed
    if dominant_ratio < 0.70:
        return "mixed"

    return dominant


# ─── FULL ANALYSIS ────────────────────────────────────────────────────────────

def _full_analysis(text: str) -> AnalysisReport:
    """
    Full structural analysis. Used on ALLOW and HEAVY_REQUIRED.
    No LLM. No I/O. Pure text heuristics.
    """
    words  = text.split()
    word_count = len(words)
    char_count = len(text)

    scripts  = _detect_scripts(text)
    dominant = _dominant_script(scripts)

    hints: list[AnalysisHint] = []

    # ── structural ────────────────────────────────────────────────────────────
    if _RE_CODE_BLOCK.search(text):
        hints.append(AnalysisHint(HintType.HAS_CODE_BLOCK, True, 0.97))

    if _RE_JSON.search(text):
        hints.append(AnalysisHint(HintType.HAS_JSON, True, 0.85))

    if _RE_MATH.search(text):
        hints.append(AnalysisHint(HintType.HAS_MATH, True, 0.80))

    if _RE_URL.search(text):
        hints.append(AnalysisHint(HintType.HAS_URL, True, 0.99))

    if _RE_LIST_ITEM.search(text) or _RE_NUMBERED_Q.search(text):
        hints.append(AnalysisHint(HintType.HAS_LIST, True, 0.90))

    # ── length ────────────────────────────────────────────────────────────────
    if word_count <= 20:
        hints.append(AnalysisHint(HintType.IS_SHORT, True, 1.0))
    elif word_count >= 200:
        hints.append(AnalysisHint(HintType.IS_LONG, True, 1.0))

    # ── multipart ─────────────────────────────────────────────────────────────
    numbered = _RE_NUMBERED_Q.findall(text)
    if len(numbered) >= 2:
        hints.append(AnalysisHint(HintType.IS_MULTIPART, True, 0.88))

    # ── script signals ────────────────────────────────────────────────────────
    if scripts["arabic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_ARABIC, True, 0.99))
    if scripts["cjk"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CJK, True, 0.99))
    if scripts["cyrillic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CYRILLIC, True, 0.99))
    if scripts["latin"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_LATIN, True, 0.99))

    if dominant == "mixed":
        hints.append(AnalysisHint(HintType.IS_MULTILINGUAL, True, 0.85))

    # ── tone heuristics ───────────────────────────────────────────────────────
    stripped = text.strip()
    if stripped.endswith(("?", "؟", "？")):
        hints.append(AnalysisHint(HintType.LIKELY_QUESTION, True, 0.95))

    first_word = words[0].lower().rstrip(".,!?") if words else ""
    command_starters = {
        "write", "make", "create", "generate", "build", "fix", "help",
        "explain", "show", "translate", "convert", "find", "search",
        "напиши", "сделай", "создай", "объясни", "покажи", "найди",
        "переведи", "исправь", "помоги",
    }
    if first_word in command_starters:
        hints.append(AnalysisHint(HintType.LIKELY_COMMAND, True, 0.82))

    return AnalysisReport(
        hints=hints,
        word_count=word_count,
        char_count=char_count,
        dominant_script=dominant,
        lightweight=False,
    )


# ─── LIGHTWEIGHT ANALYSIS (DEGRADED_MODE) ─────────────────────────────────────

def _lightweight_analysis(text: str) -> AnalysisReport:
    """
    Minimal structural analysis for DEGRADED_MODE.
    Only the fastest checks — no regex that scans full text.
    """
    words      = text.split()
    word_count = len(words)
    char_count = len(text)

    hints: list[AnalysisHint] = []

    # Only script detection and length — cheapest possible checks
    scripts  = _detect_scripts(text)
    dominant = _dominant_script(scripts)

    if scripts["arabic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_ARABIC, True, 0.99))
    if scripts["cjk"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CJK, True, 0.99))
    if scripts["cyrillic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CYRILLIC, True, 0.99))

    if word_count <= 20:
        hints.append(AnalysisHint(HintType.IS_SHORT, True, 1.0))

    if "```" in text:
        hints.append(AnalysisHint(HintType.HAS_CODE_BLOCK, True, 0.95))

    if text.strip().endswith(("?", "؟", "？")):
        hints.append(AnalysisHint(HintType.LIKELY_QUESTION, True, 0.95))

    return AnalysisReport(
        hints=hints,
        word_count=word_count,
        char_count=char_count,
        dominant_script=dominant,
        lightweight=True,
    )


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

# Compiled once: opening phrases that signal a templated/meta-commentary response.
# Used by detect_repetitive_opening() — pure heuristic, no LLM.
_RE_TEMPLATED_OPENERS = re.compile(
    r"^(?:"
    r"похоже,?\s+что|"
    r"этот\s+вопрос|"
    r"данный\s+вопрос|"
    r"изображени[ея]\s+представляет|"
    r"изображени[ея]\s+представляют|"
    r"на\s+(?:данном|этом|всех|представленных)\s+изображени|"
    r"поскольку\s+у\s+меня\s+нет|"
    r"я\s+не\s+могу\s+просмотреть|"
    r"it\s+seems\s+(like|that)|"
    r"this\s+(?:question|image|request)|"
    r"the\s+image\s+(?:shows|depicts|represents)"
    r")",
    re.IGNORECASE,
)


def detect_repetitive_opening(text: str, history: list[dict]) -> bool:
    """
    Check whether the response opening is templated AND has appeared recently.

    Two conditions must both be true to return True:
      1. The response starts with a known meta-commentary / templated phrase.
      2. The same opening (first 50 chars) appears in the last 3 assistant turns.

    This is a smart guard (ChatGPT Level 2): strip only when repetition is confirmed,
    not on every templated phrase — avoids false positives on first occurrence.

    Args:
        text:    Raw LLM output (before correction).
        history: Conversation history list[{role, content}].

    Returns:
        True  → opening is templated AND was repeated recently → strip it.
        False → leave text as-is.

    Never raises.
    """
    if not text or not text.strip():
        return False

    try:
        first_line = text.strip().split("\n")[0][:100]

        # Condition 1: starts with a known templated opener
        if not _RE_TEMPLATED_OPENERS.match(first_line):
            return False

        # Condition 2: the same opening appeared in the last 3 assistant turns
        opening_50 = first_line[:50].lower().strip()
        recent_assistant = [
            t for t in (history or []) if t.get("role") == "assistant"
        ][-3:]

        for turn in recent_assistant:
            prev_opening = (turn.get("content") or "").strip().split("\n")[0][:50].lower().strip()
            if prev_opening and prev_opening == opening_50:
                return True

        # Templated but first occurrence — correction.py strip handles it as fallback
        return False

    except Exception:
        return False

def analyse(text: str, lightweight: bool = False) -> AnalysisReport:
    """
    Entry point for the meta analysis step.

    Called automatically in the DAG before intent_engine.
    NOT called by Orchestrator.

    Args:
        text:        Raw user input (post safety pass, pre intent classification).
        lightweight: True in DEGRADED_MODE, False otherwise.

    Returns:
        AnalysisReport with structural hints.
        All hints are non-binding — intent_engine may ignore them entirely.

    Never raises. Returns an empty report on any error.
    """
    if not text or not text.strip():
        return AnalysisReport(
            hints=[],
            word_count=0,
            char_count=0,
            dominant_script="latin",
            lightweight=lightweight,
        )

    try:
        if lightweight:
            return _lightweight_analysis(text)
        return _full_analysis(text)
    except Exception:
        # Meta layer must never crash the pipeline
        return AnalysisReport(
            hints=[],
            word_count=len(text.split()),
            char_count=len(text),
            dominant_script="latin",
            lightweight=lightweight,
        )