from __future__ import annotations

"""Shared prompt-layer rules.

This module is the single source of truth for response-shaping directives.
It contains stable, reusable constraints only; no routing, no model selection,
and no language-specific fallback logic.
"""

LIVE_CONTEXT_RULE = (
    "Use live retrieved context as the current working context. "
    "Answer directly from it, and mention missing details only when that matters."
)

# Backward-compatible alias for older call sites and comments.
NO_CUTOFF_RULE = LIVE_CONTEXT_RULE

ANSWER_FIRST_RULE = (
    "Open with the answer itself. Do not lead with preambles, apologies, or meta commentary."
)

FORMAT_RULES = (
    "Use plain text. Do not use Markdown tables or Markdown headers. "
    f"{ANSWER_FIRST_RULE} "
    "Use numbered lists or dashes only when structure genuinely helps."
)

VARIATION_RULE = (
    "Write in plain text. Avoid Markdown tables, headers, and bold. "
    f"{ANSWER_FIRST_RULE} "
    "Vary sentence openings naturally."
)

__all__ = [
    "LIVE_CONTEXT_RULE",
    "NO_CUTOFF_RULE",
    "ANSWER_FIRST_RULE",
    "FORMAT_RULES",
    "VARIATION_RULE",
]