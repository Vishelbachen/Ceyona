import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── SAFETY SIGNALS ──────────────────────────────────────────────────────────

_BLOCK_PATTERNS: list[str] = [
    "how to make a bomb",
    "how to make explosives",
    "child pornography",
    "how to hack",
    "ddos attack",
    "synthesize drugs",
]


@dataclass(frozen=True)
class SafetyResult:
    safe: bool
    reason: str = ""


def check(text: str) -> SafetyResult:
    """
    Deterministic safety check on raw text.
    Pure function. No I/O. No LLM calls.
    Returns SafetyResult(safe=False) if any block pattern matched.
    """
    lower = text.lower()
    for pattern in _BLOCK_PATTERNS:
        if pattern in lower:
            logger.warning("Safety block triggered", extra={"pattern": pattern})
            return SafetyResult(safe=False, reason=f"blocked pattern: {pattern}")
    return SafetyResult(safe=True)