from __future__ import annotations

"""Shared prompt-layer rules.

These are positive behavior constraints, not language-specific fallbacks.
Keep them short, stable, and reusable across intent routing and message assembly.
"""

NO_CUTOFF_RULE = (
    "When current or grounded information is missing, say so plainly instead of inventing it. "
    "Do not imply live access to facts that are not present in your input or retrieved context. "
    "If the answer depends on freshness, prices, availability, routes, or titles and you do not have grounded evidence, "
    "ask for the missing detail or suggest a verifiable next step."
)

ANSWER_FIRST_RULE = (
    "Open with the answer itself — the first word of your response is part of the answer."
)

FORMAT_RULES = (
    "FORMATTING — mandatory: "
    "Never use Markdown tables (no | pipes |). "
    "Never use Markdown headers (no ###, ##, #). "
    f"{ANSWER_FIRST_RULE} "
    "Use plain text, numbered lists, or dashes only. "
)

VARIATION_RULE = (
    "Write in plain text. No markdown tables, no headers, no bold. "
    f"{ANSWER_FIRST_RULE} "
    "Vary your sentence openings naturally."
)

def join_rules(*rules: str) -> str:
    """Join non-empty rule fragments into a single prompt string."""
    parts = [rule.strip() for rule in rules if rule and rule.strip()]
    return " ".join(parts)

__all__ = [
    "NO_CUTOFF_RULE",
    "ANSWER_FIRST_RULE",
    "FORMAT_RULES",
    "VARIATION_RULE",
    "join_rules",
]