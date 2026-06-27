import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ─── VERDICT ─────────────────────────────────────────────────────────────────

class SafetyVerdict(str, Enum):
    ALLOW              = "allow"
    REVISE             = "revise"
    BLOCK              = "block"
    SAFETY_UNAVAILABLE = "safety_unavailable"  # LLM judge failed — distinct from ALLOW (§21)


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
    input_tokens: int = 0   # gpt-oss-safeguard-20b input tokens — billed at $0.075/1M
    output_tokens: int = 0  # gpt-oss-safeguard-20b output tokens — billed at $0.30/1M

    @property
    def safe(self) -> bool:
        # SAFETY_UNAVAILABLE is NOT safe — judge did not run.
        # Coordinator decides what to do with it (§21 architecture contract).
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
# Why LLM-judge only, no fast path (architecture.md §21):
#   The LLM judge covers ALLOW / REVISE / BLOCK semantically across all languages.
#   A keyword fast path would require per-language signal lists — a linguistic
#   crutch that grows unbounded and conflicts with the LLM verdict.
#   Fast path was removed: language-agnostic semantic classification is
#   delegated entirely to the LLM judge. (audit.md SAFETY-3)
#
# Cost tradeoff (acknowledged, per architecture decisions):
#   LLM call adds latency and tokens. Acceptable because:
#   - safety_agent runs post-reasoning, not on every message
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



async def _llm_judge(combined: str) -> tuple[SafetyVerdict, int, int]:
    """
    Ask gpt-oss-safeguard-20b to judge whether the emergent content is harmful.

    Returns (verdict, input_tokens, output_tokens) for billing.

    On any exception: returns (SAFETY_UNAVAILABLE, 0, 0).
    SAFETY_UNAVAILABLE is NOT equivalent to ALLOW — coordinator handles it explicitly (§21).
    Metric incremented: safety_agent.judge_unavailable — observability required.

    Tokens billed at gpt-oss-safeguard-20b rates (economic.md §1.2):
      input:  $0.075/1M
      output: $0.30/1M  (1-2 tokens — small but must bill)
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
        in_tok  = response.input_tokens
        out_tok = response.output_tokens

        if "BLOCK" in verdict_text:
            return SafetyVerdict.BLOCK, in_tok, out_tok
        if "REVISE" in verdict_text:
            return SafetyVerdict.REVISE, in_tok, out_tok
        return SafetyVerdict.ALLOW, in_tok, out_tok

    except Exception as exc:
        # Import here to avoid circular dependency at module load time.
        try:
            from infra.metrics import increment
            increment("safety_agent.judge_unavailable")
        except Exception:
            pass  # metrics failure must never suppress the safety signal

        logger.error(
            "safety_agent: LLM judge unavailable — returning SAFETY_UNAVAILABLE",
            extra={"error": str(exc), "event": "safety_judge_signal_lost"},
        )
        return SafetyVerdict.SAFETY_UNAVAILABLE, 0, 0


def check(inp: SafetyInput) -> SafetyResult:
    """
    Synchronous entry point — for non-async call sites only.

    MUST NOT be called from async context — raises RuntimeError immediately.
    Use await check_async() in all async code (coordinator, orchestrator).

    Fast path: none — LLM judge handles all verdicts across all languages (audit.md SAFETY-3).
    Semantic path: LLM judge via new event loop — only valid outside running event loop.

    Returns:
      ALLOW              → pass through to Consensus / Synthesizer
      REVISE             → coordinator handles per §21 contract
      BLOCK              → coordinator blocks, orchestrator renders deny message
      SAFETY_UNAVAILABLE → LLM judge failed; coordinator handles per §21 contract
    """
    import asyncio

    # §21 critical rule: calling check() from async context is a contract violation.
    # Silent ALLOW was an invisible safety hole — hard error surfaces it at dev time.
    try:
        asyncio.get_running_loop()
        # If we get here — a loop IS running — this call is illegal.
        raise RuntimeError(
            "check() is synchronous only. "
            "Use await check_async() inside async code."
        )
    except RuntimeError as exc:
        if "check() is synchronous only" in str(exc):
            raise
        # get_running_loop() raised "no running event loop" — safe to continue.

    combined = f"{inp.reasoning_plan} {inp.draft_response}"

    # No fast path — LLM judge handles ALLOW/REVISE/BLOCK across all languages.
    # See audit.md SAFETY-3 for rationale.
    try:
        loop = asyncio.new_event_loop()
        try:
            verdict, in_tok, out_tok = loop.run_until_complete(_llm_judge(combined))
        finally:
            loop.close()
    except Exception as exc:
        logger.error("safety_agent: sync runner failed", extra={"error": str(exc)})
        return SafetyResult(verdict=SafetyVerdict.SAFETY_UNAVAILABLE)

    if verdict == SafetyVerdict.BLOCK:
        logger.warning("safety_agent BLOCK", extra={"verdict": "BLOCK"})
        return SafetyResult(
            verdict=SafetyVerdict.BLOCK,
            reason="unsafe emergent content (LLM judge)",
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    if verdict == SafetyVerdict.REVISE:
        logger.info("safety_agent REVISE", extra={"verdict": "REVISE"})
        return SafetyResult(
            verdict=SafetyVerdict.REVISE,
            reason="content requires revision (LLM judge)",
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    if verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
        return SafetyResult(verdict=SafetyVerdict.SAFETY_UNAVAILABLE)

    return SafetyResult(
        verdict=SafetyVerdict.ALLOW,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )


async def check_async(inp: SafetyInput) -> SafetyResult:
    """
    Async entry point — preferred for all coordinator/orchestrator paths.

    Fast path: none — LLM judge handles all verdicts across all languages (audit.md SAFETY-3).
    Semantic path: LLM judge (gpt-oss-safeguard-20b).

    Returns:
      ALLOW              → pass through to Consensus / Synthesizer
      REVISE             → coordinator handles per §21 contract
      BLOCK              → coordinator blocks, orchestrator renders deny message
      SAFETY_UNAVAILABLE → LLM judge failed; coordinator handles per §21 contract
    """
    combined = f"{inp.reasoning_plan} {inp.draft_response}"

    # No fast path — LLM judge handles ALLOW/REVISE/BLOCK across all languages.
    # See audit.md SAFETY-3 for rationale.
    verdict, in_tok, out_tok = await _llm_judge(combined)

    if verdict == SafetyVerdict.BLOCK:
        logger.warning("safety_agent BLOCK", extra={"verdict": "BLOCK"})
        return SafetyResult(
            verdict=SafetyVerdict.BLOCK,
            reason="unsafe emergent content (LLM judge)",
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    if verdict == SafetyVerdict.REVISE:
        logger.info("safety_agent REVISE", extra={"verdict": "REVISE"})
        return SafetyResult(
            verdict=SafetyVerdict.REVISE,
            reason="content requires revision (LLM judge)",
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    if verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
        logger.warning("safety_agent UNAVAILABLE", extra={"verdict": "SAFETY_UNAVAILABLE"})
        return SafetyResult(verdict=SafetyVerdict.SAFETY_UNAVAILABLE)

    return SafetyResult(
        verdict=SafetyVerdict.ALLOW,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )