from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ─── VERDICT ─────────────────────────────────────────────────────────────────

class SafetyVerdict(str, Enum):
    ALLOW  = "allow"
    REVISE = "revise"
    BLOCK  = "block"


# ─── CONTRACTS ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SafetyInput:
    reasoning_plan: str    # from reasoning_engine
    draft_response: str    # from primary agent
    user_message: str      # original user input


@dataclass(frozen=True)
class SafetyResult:
    verdict: SafetyVerdict
    reason: str = ""

    @property
    def safe(self) -> bool:
        return self.verdict == SafetyVerdict.ALLOW


# ─── SEMANTIC SIGNALS ────────────────────────────────────────────────────────
# safety_agent validates EMERGENT content in reasoning + draft response.
# It does NOT duplicate Safety Layer (Pass 1/2 keyword/classifier gates).
# It catches unsafe content that emerges from the reasoning process itself.

_BLOCK_SIGNALS: list[str] = [
    "step-by-step instructions to harm",
    "how to synthesize",
    "detailed exploit",
    "working malware",
    "child sexual",
]

_REVISE_SIGNALS: list[str] = [
    "i cannot verify this is safe",
    "this may cause harm",
    "consult a professional",
    "not medical advice",
    "not legal advice",
]


def check(inp: SafetyInput) -> SafetyResult:
    """
    Semantic safety validation of reasoning plan and draft response.

    Position in pipeline:
      ACTIVE on ALLOW / HEAVY_REQUIRED
      SKIP on DEGRADED_MODE / DENY
      LAST in Agent Layer before Consensus

    Does NOT duplicate Safety Layer:
      Safety Layer → deterministic firewall on raw input
      safety_agent → semantic validation of emergent LLM output

    Returns:
      ALLOW  → pass through to Consensus / Synthesizer
      REVISE → coordinator may retry or flag for review
      BLOCK  → coordinator blocks, orchestrator renders deny message
    """
    combined = f"{inp.reasoning_plan} {inp.draft_response}".lower()

    for signal in _BLOCK_SIGNALS:
        if signal in combined:
            logger.warning("safety_agent BLOCK", extra={"signal": signal})
            return SafetyResult(
                verdict=SafetyVerdict.BLOCK,
                reason=f"unsafe emergent content: {signal}",
            )

    for signal in _REVISE_SIGNALS:
        if signal in combined:
            logger.info("safety_agent REVISE", extra={"signal": signal})
            return SafetyResult(
                verdict=SafetyVerdict.REVISE,
                reason=f"response requires revision: {signal}",
            )

    return SafetyResult(verdict=SafetyVerdict.ALLOW)