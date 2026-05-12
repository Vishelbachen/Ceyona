from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

import agents.creative_agent as creative_agent
import agents.deep_agent as deep_agent
import agents.fast_agent as fast_agent
from agents.consensus_engine import ConsensusResult, resolve
from agents.fast_agent import AgentResult
from agents.safety_agent import SafetyInput, SafetyResult, SafetyVerdict, check as safety_check
from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


# ─── AGENT IDENTIFIERS ────────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST     = "fast"
    DEEP     = "deep"
    CREATIVE = "creative"


# ─── PLAN CONTRACT ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    fallback: AgentType | None
    use_consensus: bool = False
    parallel_validators: list[AgentType] = field(default_factory=list)
    temperature: float = 0.7


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass
class CoordinationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    blocked: bool = False
    block_reason: str = ""


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select agent plan based on intent + tier + strategy.
    Pure function. No I/O. No state. No LLM calls.
    NO policy authority. NO routing decisions.

    HEAVY_REQUIRED tier:
      primary=DEEP, no consensus (mutex), no Fast validators.
    ALLOW tier:
      Fast → General → Agents → safety_agent → Consensus.
    DEGRADED_MODE:
      Fast only (orchestrator routes here directly, plan is minimal).
    """
    # HEAVY_REQUIRED — consensus is skipped (mutex with Heavy Tier)
    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # DEGRADED_MODE — Fast only
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # ALLOW — GENERAL tier
    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    if intent in (Intent.CODE, Intent.MATH, Intent.ANALYSIS, Intent.QUESTION, Intent.INSTRUCTION):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # Tool-result synthesis intents — need DEEP to properly synthesise
    # external data (search snippets, route data, weather) into a coherent answer.
    # Previously fell through to default FAST with no fallback:
    #   FAST agent (llama-3.1-8b, 512 tokens) received 5 search snippets +
    #   system prompt → context overflow or empty response → coordinator blocked.
    if intent in (
        Intent.SEARCH,
        Intent.WEATHER,
        Intent.MAPS,
        Intent.MAPS_POI,
        Intent.MAPS_ROUTE,
    ):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # EMOTIONAL — fast, warm, low temperature for natural empathetic tone
    if intent == Intent.EMOTIONAL:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=None,
            use_consensus=False,
            parallel_validators=[],
            temperature=0.85,
        )

    # default GENERAL — FAST for conversation, search results, etc.
    return AgentPlan(
        primary=AgentType.FAST,
        fallback=None,
        use_consensus=False,
        parallel_validators=[],
        temperature=strategy.temperature,
    )


# ─── AGENT DISPATCHER ─────────────────────────────────────────────────────────

async def _run_agent(
    agent_type: AgentType,
    messages: list[dict],
    temperature: float = 0.7,
) -> AgentResult:
    """
    Dispatch to the correct agent module.
    Never raises — returns AgentResult(success=False) on any error.
    """
    try:
        if agent_type == AgentType.FAST:
            return await fast_agent.run(messages, temperature=temperature)
        if agent_type == AgentType.DEEP:
            return await deep_agent.run(messages, temperature=temperature)
        if agent_type == AgentType.CREATIVE:
            return await creative_agent.run(messages, temperature=temperature)
    except Exception as exc:
        logger.error("Agent dispatch error", extra={
            "agent": agent_type, "error": str(exc),
        }, exc_info=True)
    return AgentResult(text="", model="", input_tokens=0, output_tokens=0, success=False)


def _agent_succeeded(result: AgentResult) -> bool:
    return result.success and bool(result.text.strip())


# ─── MAIN COORDINATOR ─────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
    reasoning_plan: str = "",
    temperature: float = 0.7,
    intent: Intent | None = None,
    lang: str = "en",
) -> CoordinationResult:
    """
    Execute agent plan. Return CoordinationResult to orchestrator.

    Pipeline (ALLOW path):
      1. Primary agent
      2. Parallel validators (if any)
      3. safety_agent — LAST before Consensus (post-reasoning semantic validation)
      4. Consensus (ALLOW only, mutex with HEAVY)

    Pipeline (HEAVY_REQUIRED path):
      1. Primary agent (DEEP)
      2. safety_agent — mandatory
      3. Response Synthesizer aggregates directly (no Consensus)

    Pipeline (DEGRADED_MODE path):
      1. Fast agent only
      (safety_agent skipped on DEGRADED per architecture)

    GUARANTEE: blocked=False → text is always non-empty.
               blocked=True  → orchestrator renders deny message.
    """

    # ── primary agent ─────────────────────────────────────────────────────────
    primary_result = await _run_agent(plan.primary, messages, temperature)

    # ── consensus path (ALLOW only) ───────────────────────────────────────────
    if plan.use_consensus:
        if plan.parallel_validators:
            tasks = [
                _run_agent(vt, messages, temperature)
                for vt in plan.parallel_validators
            ]
            validator_results: list[AgentResult] = await asyncio.gather(*tasks)
        else:
            validator_results = []

        candidates = [
            r for r in [primary_result, *validator_results]
            if _agent_succeeded(r)
        ]

        # safety_agent: LAST before Consensus
        if candidates:
            best_candidate = max(candidates, key=lambda r: len(r.text))
            safety: SafetyResult = safety_check(SafetyInput(
                reasoning_plan=reasoning_plan,
                draft_response=best_candidate.text,
                user_message=user_message,
            ))
            if safety.verdict == SafetyVerdict.BLOCK:
                logger.warning("safety_agent BLOCK before consensus",
                               extra={"reason": safety.reason})
                return CoordinationResult(
                    text="", model="", input_tokens=0, output_tokens=0,
                    blocked=True, block_reason="safety_block",
                )

        if candidates:
            consensus: ConsensusResult = await resolve(candidates)
            if consensus.text:
                return CoordinationResult(
                    text=consensus.text,
                    model=consensus.model,
                    input_tokens=consensus.input_tokens,
                    output_tokens=consensus.output_tokens,
                )

        logger.warning("All consensus candidates failed — attempting fallback")

    # ── primary succeeded (non-consensus path) ────────────────────────────────
    if _agent_succeeded(primary_result):
        # HEAVY path: safety_agent mandatory
        # DEGRADED path: safety_agent skipped (no parallel_validators, fallback is FAST==primary)
        is_heavy = not plan.use_consensus and plan.parallel_validators == [] and plan.fallback != plan.primary
        if is_heavy:
            safety = safety_check(SafetyInput(
                reasoning_plan=reasoning_plan,
                draft_response=primary_result.text,
                user_message=user_message,
            ))
            if safety.verdict == SafetyVerdict.BLOCK:
                logger.warning("safety_agent BLOCK on HEAVY path",
                               extra={"reason": safety.reason})
                return CoordinationResult(
                    text="", model="", input_tokens=0, output_tokens=0,
                    blocked=True, block_reason="safety_block",
                )

        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            input_tokens=primary_result.input_tokens,
            output_tokens=primary_result.output_tokens,
        )

    # ── primary failed → fallback ─────────────────────────────────────────────
    logger.warning("Primary agent failed", extra={
        "agent": plan.primary,
        "error": getattr(primary_result, "error", ""),
    })

    if plan.fallback is not None and plan.fallback != plan.primary:
        logger.info("Trying fallback agent", extra={"agent": plan.fallback})
        fallback_result = await _run_agent(plan.fallback, messages, temperature)

        if _agent_succeeded(fallback_result):
            logger.info("Fallback agent succeeded")
            return CoordinationResult(
                text=fallback_result.text,
                model=fallback_result.model,
                input_tokens=fallback_result.input_tokens,
                output_tokens=fallback_result.output_tokens,
            )

        logger.error("Fallback agent also failed",
                     extra={"agent": plan.fallback})

    # ── all failed ────────────────────────────────────────────────────────────
    logger.error("All agents failed — returning blocked result")

    # Graceful fallback for EMOTIONAL intent: rule-based empathy response
    # avoids showing a cold error message when the user just vented.
    if intent == Intent.EMOTIONAL:
        _EMOTIONAL_FALLBACK: dict[str, str] = {
            "ru": "Понимаю, это неприятно. Расскажи, что случилось — постараюсь помочь.",
            "en": "That sounds rough. Want to tell me more about what happened?",
            "de": "Das klingt wirklich frustrierend. Erzähl mir, was passiert ist.",
            "fr": "Ça a l'air difficile. Dis-moi ce qui s'est passé.",
            "es": "Entiendo, eso es difícil. Cuéntame qué pasó.",
            "pt": "Entendo, isso é difícil. Me conta o que aconteceu.",
            "it": "Capisco, sembra brutto. Dimmi cosa è successo.",
            "tr": "Anlıyorum, bu zor. Ne olduğunu anlatır mısın?",
            "ar": "أفهم ذلك، يبدو صعباً. أخبرني ماذا حدث.",
            "zh": "听起来很糟。跟我说说发生了什么？",
            "ja": "それは大変だったね。何があったか話してみて。",
            "ko": "힘들었겠네요. 무슨 일이 있었는지 얘기해줄래요?",
            "pl": "Rozumiem, to musi być frustrujące. Opowiedz, co się stało.",
            "uk": "Розумію, це неприємно. Розкажи, що сталося.",
            "fa": "می‌فهمم، این سخته. بگو چی شده.",
            "nl": "Dat klinkt vervelend. Vertel me wat er is gebeurd.",
            "sv": "Det låter jobbigt. Berätta vad som hände.",
            "no": "Det høres tøft ut. Fortell meg hva som skjedde.",
            "da": "Det lyder svært. Fortæl mig hvad der skete.",
            "fi": "Kuulostaa raskaalta. Kerro mitä tapahtui.",
            "he": "נשמע קשה. ספר לי מה קרה.",
            "hi": "समझ सकता हूँ, यह मुश्किल है। बताओ क्या हुआ।",
            "id": "Kedengarannya berat. Ceritakan apa yang terjadi.",
            "az": "Anlayıram, bu çətindir. De görüm nə baş verdi.",
            "kk": "Түсінемін, бұл ауыр. Не болғанын айтшы.",
            "uz": "Tushunaman, bu qiyin. Nima bo'lganini ayt.",
            "ka": "მესმის, ეს ძნელია. მიამბე, რა მოხდა.",
            "hy": "Հասկանում եմ, դա ծանր է: Պատմիր՝ ինչ եղավ:",
            "mn": "Ойлгож байна, энэ хэцүү. Юу болсноо хэлж өгнө үү.",
            "sw": "Naelewa, ni vigumu. Niambie kilichotokea.",
        }
        fallback_text = _EMOTIONAL_FALLBACK.get(lang) or _EMOTIONAL_FALLBACK["en"]
        logger.info("EMOTIONAL graceful fallback used", extra={"lang": lang})
        return CoordinationResult(
            text=fallback_text,
            model="rule-based-fallback",
            input_tokens=0,
            output_tokens=0,
        )

    return CoordinationResult(
        text="", model="", input_tokens=0, output_tokens=0,
        blocked=True, block_reason="no_response",
    )