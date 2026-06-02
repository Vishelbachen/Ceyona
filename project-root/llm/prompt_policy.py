from __future__ import annotations

"""Shared prompt-layer rules.

These are positive behavior constraints, not language-specific fallbacks.
Keep them short, stable, and reusable across intent routing and message assembly.
"""

NO_CUTOFF_RULE = (
    "GROUNDING RULE: treat live tool output as current only when it is present in the request context. "
    "If evidence is missing, incomplete, or conflicting, say so plainly and ask for more context when helpful. "
    "Do not invent freshness, prices, availability, routes, or facts that are not grounded in the input. "
    "Never imply certainty without evidence."
)

NO_CARRYOVER_RULE = (
    "HISTORY RULE: use only conversation turns that are relevant to the current request. "
    "Do not carry over names, places, titles, or other facts from an unrelated previous topic just because they were recent. "
    "If history is irrelevant or ambiguous, ignore it instead of blending topics."
)

ANSWER_FIRST_RULE = (
    "Open with the answer itself — the first word of your response is part of the answer."
)


NO_UNSOLICITED_CODE_RULE = (
    "CODE POLICY: do not output code, code blocks, stack traces, or scripts unless the user explicitly asks for code. "
    "If the answer would otherwise contain code or a program listing in a non-code intent, replace it with a plain-language explanation or a short clarification instead."
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
    "NO_CARRYOVER_RULE",
    "ANSWER_FIRST_RULE",
    "NO_UNSOLICITED_CODE_RULE",
    "FORMAT_RULES",
    "VARIATION_RULE",
    "join_rules",
]