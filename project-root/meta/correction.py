from __future__ import annotations

import re


# ─── BOILERPLATE PATTERNS TO STRIP ────────────────────────────────────────────
# These are common LLM preamble / sign-off artifacts that add no value.
# Matched case-insensitively at the start or end of the response.

_PREAMBLE_PATTERNS: list[re.Pattern] = [
    # "Sure! Here is..." / "Of course! ..."
    re.compile(r"^(sure[!,.]?\s*|of course[!,.]?\s*|certainly[!,.]?\s*|absolutely[!,.]?\s*|great[!,.]?\s*)", re.IGNORECASE),
    # "Here is your ..." / "Here's the ..."
    re.compile(r"^(here(?:'s| is)(?: your| the)?\s+(?:answer|response|result|code|explanation|text|solution)[:\s]*\n*)", re.IGNORECASE),
    # "I'd be happy to help..." / "I'm happy to assist..."
    re.compile(r"^(i(?:'d| would) be (?:happy|glad|delighted) to (?:help|assist)[!.,]?\s*\n*)", re.IGNORECASE),
    # "As an AI language model, ..."
    re.compile(r"^(as an ai(?: language)? model[,.]?\s*)", re.IGNORECASE),
    # "I hope this helps!" at the end
    re.compile(r"\n*i hope (?:this|that) (?:helps|was helpful)[!.]?\s*$", re.IGNORECASE),
    # "Let me know if you have any questions!"
    re.compile(r"\n*(?:please )?let me know if you(?:'ve| have) any (?:more )?questions[!.]?\s*$", re.IGNORECASE),
    # "Feel free to ask if you need anything else!"
    re.compile(r"\n*feel free to (?:ask|reach out)[^.!?\n]{0,60}[!.]?\s*$", re.IGNORECASE),
    # "Is there anything else I can help you with?"
    re.compile(r"\n*is there anything else i(?: can| could)(?: help you with)?[?!.]?\s*$", re.IGNORECASE),
]

# ─── MARKDOWN FIXERS ──────────────────────────────────────────────────────────

_RE_TRIPLE_BACKTICK = re.compile(r"```")
_RE_BOLD_MARKER     = re.compile(r"\*\*")
_RE_ITALIC_MARKER   = re.compile(r"(?<!\*)\*(?!\*)")

# ─── WHITESPACE ───────────────────────────────────────────────────────────────

_RE_EXCESSIVE_BLANKS = re.compile(r"\n{4,}")
_RE_TRAILING_SPACE   = re.compile(r"[ \t]+$", re.MULTILINE)


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _strip_preamble(text: str) -> str:
    """Remove common LLM boilerplate from start and end."""
    for pattern in _PREAMBLE_PATTERNS:
        text = pattern.sub("", text)
    return text


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
    Apply lightweight text correction.

    Called exclusively by response_synthesizer at step 4.
    Must never raise — caller (synthesizer) handles exceptions by keeping original.

    Pipeline:
      1. Strip LLM boilerplate preambles / sign-offs
      2. Fix unclosed markdown markers
      3. Normalise whitespace

    Returns corrected text. If result would be empty, returns original.
    """
    if not text or not text.strip():
        return text

    result = _strip_preamble(text)
    result = _fix_markdown(result)
    result = _normalise_whitespace(result)

    # Safety: never return empty — synthesizer will discard anyway, but be explicit
    return result if result.strip() else text