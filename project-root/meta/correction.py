from __future__ import annotations

import re
from collections.abc import Sequence

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Deterministic structural cleanup step in the synthesizer pipeline (step 5).
# Position: after normalize_telegram, before output_normalizer.
#
# What this module does:
#   ✓ Fix unclosed Markdown markers (odd ``` or ** counts)
#   ✓ Remove exact repeated blocks created by looping generations
#   ✓ Normalise whitespace (trailing spaces, excessive blank lines)
#
# What this module does NOT do:
#   ✗ Strip preamble phrases by language  ← this is the prompt's job
#   ✗ Suppress specific words or synonyms ← whack-a-mole, does not scale
#   ✗ Make routing or policy decisions
#
# Preamble suppression rationale:
#   Listing prohibited phrases here is a losing strategy — the model finds
#   synonyms: ban "Конечно!" → it writes "Разумеется!" → ban that →
#   "С удовольствием!" → indefinitely, with no end and with asymmetric
#   coverage across languages. The correct fix is prompt-layer policy in
#   llm.prompt_policy.FORMAT_RULES / llm.prompt_policy.VARIATION_RULE and
#   intent_engine._FORMAT_RULES. correction.py is the last-resort structural
#   cleaner, not a style enforcer.
#
# Authority boundary: architecture.md §19, models.md §10.


# ─── MARKDOWN FIXERS ──────────────────────────────────────────────────────────

_RE_TRIPLE_BACKTICK = re.compile(r"```")
_RE_BOLD_MARKER = re.compile(r"\*\*")

# ─── PIPE TABLE STRIPPER ─────────────────────────────────────────────────────
# FORMAT_RULES prohibits Markdown tables, but compound (synthesizer) occasionally
# outputs them anyway. Strip pipe-table rows deterministically here so the
# prompt instruction has a hard backstop.
#
# Two patterns removed:
#   • Data/header rows: lines that start and end with | (e.g. "| col | col |")
#   • Separator rows:   lines of dashes/pipes (e.g. "|---|---|")
#
# Rows are removed entirely — the surrounding text (if any) is kept.
# This is structural cleanup, not translation; meaning is never changed.

_RE_PIPE_TABLE_ROW = re.compile(r"^\|.+\|$", re.MULTILINE)
_RE_PIPE_SEPARATOR_ROW = re.compile(r"^\|[-+: |]+\|$", re.MULTILINE)

# ─── REPETITION CLEANUP ──────────────────────────────────────────────────────

_RE_BLANK_SPLIT = re.compile(r"(?:\r?\n){2,}")

# ─── WHITESPACE ───────────────────────────────────────────────────────────────

_RE_EXCESSIVE_BLANKS = re.compile(r"\n{4,}")
_RE_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _strip_pipe_tables(text: str) -> str:
    """
    Remove Markdown pipe-table rows from text.

    Removes both data rows (| col | col |) and separator rows (|---|---|).
    Collapses any resulting excessive blank lines.
    Called before whitespace normalisation so _normalise_whitespace cleans up.
    """
    result = _RE_PIPE_TABLE_ROW.sub("", text)
    result = _RE_PIPE_SEPARATOR_ROW.sub("", result)
    return result


def _fix_markdown(text: str) -> str:
    """
    Fix unclosed markdown markers.
    Rule: if a marker appears an odd number of times → append a closing marker.
    Only applied to triple backticks and bold (**) — safest heuristics.
    """
    # Triple backticks: odd count → unclosed code block
    backtick_count = len(_RE_TRIPLE_BACKTICK.findall(text))
    if backtick_count % 2 != 0:
        text = text.rstrip() + "\n```"

    # Bold markers: odd count → unclosed bold
    bold_count = len(_RE_BOLD_MARKER.findall(text))
    if bold_count % 2 != 0:
        text = text.rstrip() + "**"

    return text


def _dedupe_consecutive_paragraphs(text: str) -> str:
    """Collapse exact paragraph repeats produced by looped generations."""
    parts = _RE_BLANK_SPLIT.split(text.strip())
    if len(parts) < 2:
        return text

    deduped: list[str] = []
    prev: str | None = None
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        if prev is not None and chunk == prev:
            continue
        deduped.append(chunk)
        prev = chunk
    return "\n\n".join(deduped)


def _dedupe_consecutive_lines(text: str) -> str:
    """Drop immediately repeated lines while keeping the first occurrence."""
    lines = text.splitlines()
    if len(lines) < 2:
        return text

    cleaned: list[str] = []
    prev_key: str | None = None
    for line in lines:
        key = line.strip()
        if key and key == prev_key:
            continue
        cleaned.append(line)
        prev_key = key if key else None
    return "\n".join(cleaned)


def _normalise_whitespace(text: str) -> str:
    """Collapse 4+ consecutive blank lines to 2, strip trailing spaces per line."""
    text = _RE_TRAILING_SPACE.sub("", text)
    text = _RE_EXCESSIVE_BLANKS.sub("\n\n\n", text)
    return text.strip()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def apply(text: str, history: Sequence[dict] | None = None) -> str:
    """
    Apply lightweight structural correction.

    Called exclusively by response_synthesizer at step 5.
    Must never raise — caller handles exceptions by keeping original.

    Pipeline:
      1. Fix unclosed markdown markers
      2. Remove exact repeated blocks
      3. Normalise whitespace

    The history argument is accepted for future repetition-aware cleanup; the
    current implementation stays purely structural and does not rewrite intent.

    Returns corrected text. If result would be empty, returns original.
    """
    if not text or not text.strip():
        return text

    result = _strip_pipe_tables(text)
    result = _fix_markdown(result)
    result = _dedupe_consecutive_lines(result)
    result = _dedupe_consecutive_paragraphs(result)
    result = _normalise_whitespace(result)

    # Safety: never return empty
    return result if result.strip() else text