from __future__ import annotations

import re

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Deterministic structural cleanup step in the synthesizer pipeline (step 5).
# Position: after normalize_telegram, before output_normalizer.
#
# What this module does:
#   ✓ Fix unclosed Markdown markers (odd ``` or ** counts)
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
#   coverage across languages. The correct fix is a target-pattern prompt
#   instruction enforced in intent_engine._FORMAT_RULES and prompt_engine
#   _variation_rule: "Open with the answer itself. First word of your
#   response is part of the answer." correction.py is the last-resort
#   structural cleaner, not a style enforcer.
#
# Authority boundary: architecture.md §19, models.md §10.


# ─── MARKDOWN FIXERS ──────────────────────────────────────────────────────────

_RE_TRIPLE_BACKTICK = re.compile(r"```")
_RE_BOLD_MARKER     = re.compile(r"\*\*")

# ─── WHITESPACE ───────────────────────────────────────────────────────────────

_RE_EXCESSIVE_BLANKS = re.compile(r"\n{4,}")
_RE_TRAILING_SPACE   = re.compile(r"[ \t]+$", re.MULTILINE)


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

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


def _normalise_whitespace(text: str) -> str:
    """Collapse 4+ consecutive blank lines to 2, strip trailing spaces per line."""
    text = _RE_TRAILING_SPACE.sub("", text)
    text = _RE_EXCESSIVE_BLANKS.sub("\n\n\n", text)
    return text.strip()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def apply(text: str) -> str:
    """
    Apply lightweight structural correction.

    Called exclusively by response_synthesizer at step 5.
    Must never raise — caller handles exceptions by keeping original.

    Pipeline:
      1. Fix unclosed markdown markers
      2. Normalise whitespace

    Returns corrected text. If result would be empty, returns original.
    """
    if not text or not text.strip():
        return text

    result = _fix_markdown(text)
    result = _normalise_whitespace(result)

    # Safety: never return empty
    return result if result.strip() else text