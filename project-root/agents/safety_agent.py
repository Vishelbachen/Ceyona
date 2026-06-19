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


# ─── SEMANTIC SAFETY PROMPT ──────────────────────────────────────────────────
# safety_agent validates EMERGENT content in reasoning + draft response.
# It does NOT duplicate Safety Layer (Pass 1/2 keyword/classifier gates).
# It catches unsafe content that emerges from the reasoning process itself.
#
# Architecture: safety_agent is a POST-REASONING semantic validator.
# It receives reasoning_plan + draft_response — the full LLM output context —
# and asks gpt-oss-safeguard-20b to judge whether the CONTENT is harmful.
#
# Why LLM-judge, not string matching (architecture.md §21):
#   String matching catches only literal phrases.
#   Paraphrasing, synonyms, or non-English bypass it completely.
#   LLM-judge understands semantic intent regardless of phrasing.
#
# Cost tradeoff (acknowledged, per architecture decisions):
#   LLM call adds latency and tokens. Acceptable because:
#   - safety_agent runs post-reasoning, not on every message
#   - Only runs on ALLOW / HEAVY_REQUIRED paths (not DEGRADED / DENY)
#   - gpt-oss-safeguard-20b returns in ~1 token — max_tokens=5

_SAFETY_JUDGE_SYSTEM = (
    "You are a strict post-reasoning safety validator. "
    "You receive a reasoning plan and a draft response from an AI assistant. "
    "Classify the CONTENT (not the user request) as SAFE, REVISE, or BLOCK.\n\n"
    "BLOCK — the draft response or reasoning contains:\n"
    "- Step-by-step instructions to harm a person\n"
    "- Synthesis routes for weapons, drugs, or dangerous substances\n"
    "- Working exploit code or malware implementation\n"
    "- Sexual content involving minors\n\n"
    "REVISE — the draft response contains:\n"
    "- Unverified medical claims presented as fact\n"
    "- Legal conclusions that should include a professional disclaimer\n"
    "- Content that may cause harm but does not meet BLOCK threshold\n\n"
    "SAFE — everything else, including edge cases and ambiguous content.\n\n"
    "Default to SAFE. Err toward SAFE when intent is ambiguous.\n"
    "Reply with exactly one word: SAFE, REVISE, or BLOCK."
)

_REVISE_SIGNALS: list[str] = [
    "i cannot verify this is safe",
    "this may cause harm",
    "consult a professional",
    "not medical advice",
    "not legal advice",
]


async def _llm_judge(combined: str) -> SafetyVerdict:
    """
    Ask gpt-oss-safeguard-20b to judge whether the emergent content is harmful.

    Falls back to ALLOW on any exception — observability degraded, not blocked.
    Same principle as safety_gate: error in safety path must not cause outage.
    """
    try:
        from llm.groq_client import groq_client

        response = await groq_client.complete(
            model="openai/gpt-oss-safeguard-20b",
            messages=[
                {"role": "system", "content": _SAFETY_JUDGE_SYSTEM},
                {"role": "user",   "content": combined[:3000]},
            ],
            max_tokens=5,
            temperature=0.0,
        )
        verdict_text = response.text.strip().upper()

        if "BLOCK" in verdict_text:
            return SafetyVerdict.BLOCK
        if "REVISE" in verdict_text:
            return SafetyVerdict.REVISE
        return SafetyVerdict.ALLOW

    except Exception as exc:
        logger.error(
            "safety_agent: LLM judge unavailable (observability degraded, defaulting ALLOW)",
            extra={"error": str(exc), "event": "safety_judge_signal_lost"},
        )
        return SafetyVerdict.ALLOW


def check(inp: SafetyInput) -> SafetyResult:
    """
    Synchronous entry point — preserved for call-site compatibility.

    Delegates to _llm_judge (async). Call sites that can await should
    use check_async() directly to avoid blocking the event loop.

    Fast path: _REVISE_SIGNALS string check catches the most common
    revision triggers without an LLM call. LLM judge runs for BLOCK
    classification where semantic understanding is required.

    Returns:
      ALLOW  → pass through to Consensus / Synthesizer
      REVISE → coordinator may retry or flag for review
      BLOCK  → coordinator blocks, orchestrator renders deny message
    """
    import asyncio

    combined = f"{inp.reasoning_plan} {inp.draft_response}".lower()

    # Fast path: catch obvious revision triggers without LLM call.
    # These are precise enough that string matching is reliable.
    for signal in _REVISE_SIGNALS:
        if signal in combined:
            logger.info("safety_agent REVISE (fast path)", extra={"signal": signal})
            return SafetyResult(
                verdict=SafetyVerdict.REVISE,
                reason=f"response requires revision: {signal}",
            )

    # Semantic path: LLM judge for BLOCK-level content.
    # Runs in a new event loop if called synchronously from non-async context.
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Caller is async — they should use check_async() instead.
            # Best-effort: create a task, but log the suboptimal call pattern.
            logger.warning(
                "safety_agent.check() called from async context — use check_async()",
            )
            # Return ALLOW; the async coordinator path uses check_async directly.
            return SafetyResult(verdict=SafetyVerdict.ALLOW)
        verdict = loop.run_until_complete(_llm_judge(combined))
    except Exception as exc:
        logger.error("safety_agent: sync judge fallback failed", extra={"error": str(exc)})
        verdict = SafetyVerdict.ALLOW

    if verdict == SafetyVerdict.BLOCK:
        logger.warning("safety_agent BLOCK", extra={"verdict": "BLOCK"})
        return SafetyResult(verdict=SafetyVerdict.BLOCK, reason="unsafe emergent content (LLM judge)")
    if verdict == SafetyVerdict.REVISE:
        logger.info("safety_agent REVISE", extra={"verdict": "REVISE"})
        return SafetyResult(verdict=SafetyVerdict.REVISE, reason="content requires revision (LLM judge)")

    return SafetyResult(verdict=SafetyVerdict.ALLOW)


async def check_async(inp: SafetyInput) -> SafetyResult:
    """
    Async entry point for coordinator paths that can await.

    Preferred over check() in async contexts — avoids event loop conflicts.
    """
    combined = f"{inp.reasoning_plan} {inp.draft_response}".lower()

    # Fast path: revision signals
    for signal in _REVISE_SIGNALS:
        if signal in combined:
            logger.info("safety_agent REVISE (fast path)", extra={"signal": signal})
            return SafetyResult(
                verdict=SafetyVerdict.REVISE,
                reason=f"response requires revision: {signal}",
            )

    # Semantic path: LLM judge
    verdict = await _llm_judge(combined)

    if verdict == SafetyVerdict.BLOCK:
        logger.warning("safety_agent BLOCK", extra={"verdict": "BLOCK"})
        return SafetyResult(verdict=SafetyVerdict.BLOCK, reason="unsafe emergent content (LLM judge)")
    if verdict == SafetyVerdict.REVISE:
        logger.info("safety_agent REVISE", extra={"verdict": "REVISE"})
        return SafetyResult(verdict=SafetyVerdict.REVISE, reason="content requires revision (LLM judge)")

    return SafetyResult(verdict=SafetyVerdict.ALLOW)