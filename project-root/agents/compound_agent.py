from __future__ import annotations

"""
Compound Agent — synthesis execution layer.

groq/compound and groq/compound-mini are Groq's autonomous agentic systems
with built-in tools (web search, code execution). They do NOT accept custom
tool schemas via the tool-calling API — attempting to pass tools= causes a
400 invalid_request_error (verified May 2026, audit §13.1).

Architecture decision (май 2026):
  compound is used as a SYNTHESIZER, not as an autonomous agent.
  - External retrieval (Tavily / SerpAPI / SearXNG / OpenWeatherMap / Mapbox)
    is performed by the orchestrator BEFORE compound is called.
  - Retrieved context is injected into the user turn via _build_messages()
    in orchestrator.py, following the standard PromptContext pipeline.
  - compound receives messages with context already assembled and synthesizes
    the final response — it does not self-search, does not call tools.

Why this is correct:
  - Preserves source_credibility.py filtering (architecture §20)
  - Preserves TruthMode.STRICT grounding invariant (architecture §10)
  - Preserves retrieval pipeline ownership (architecture §3)
  - Eliminates 400 errors caused by unsupported tool_choice parameter
  - compound's synthesis quality (GPT-OSS-120B backbone) is fully utilised

Architecture contract:
  - No policy authority. No model selection. No routing decisions.
  - No tool schemas. No tool execution. No tool loop.
  - Receives pre-assembled messages from coordinator; synthesizes; returns AgentResult.
  - On any failure: returns AgentResult(success=False) — coordinator handles fallback.
"""

import logging

from agents.fast_agent import AgentResult
from contracts.shared_types import Tier
from llm.groq_client import groq_client
from llm.model_router import DEEP_AGENT_MODEL, FAST_AGENT_MODEL, route_max_tokens

logger = logging.getLogger(__name__)


async def _run_compound(
    model: str,
    tier: Tier,
    messages: list[dict],
    temperature: float,
) -> AgentResult:
    """
    Call compound model as a plain synthesizer.

    No tools. No tool loop. Single completion call.
    Retrieved context is already present in messages (injected by orchestrator
    via _build_messages → PromptContext → user turn).

    Returns AgentResult. Never raises — catches all exceptions.
    """
    max_tokens = route_max_tokens(tier)

    try:
        result = await groq_client.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        logger.error(
            "compound_agent: API call failed",
            extra={
                "model": model,
                "error": str(exc),
                "type":  type(exc).__name__,
            },
        )
        return AgentResult(
            text="", model=model, input_tokens=0,
            output_tokens=0, success=False, error=str(exc),
            tool_calls=0,
        )

    logger.info(
        "compound_agent: synthesis complete",
        extra={
            "model":         result.model,
            "input_tokens":  result.input_tokens,
            "output_tokens": result.output_tokens,
            "has_text":      bool(result.text.strip()),
        },
    )

    return AgentResult(
        text=result.text,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        success=bool(result.text.strip()),
        tool_calls=0,  # compound no longer executes external tools
        usage_breakdown=getattr(result, "usage_breakdown", []),
    )


async def run_fast(
    messages: list[dict],
    lang: str = "en",
    temperature: float = 0.7,
) -> AgentResult:
    """
    Compound fast synthesizer — groq/compound-mini (FAST_AGENT_MODEL).
    Low latency. Used for SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE on Tier.FAST.
    lang is accepted for interface compatibility but not passed to complete()
    (language is already enforced via system prompt in messages).
    """
    return await _run_compound(
        model=FAST_AGENT_MODEL,
        tier=Tier.FAST,
        messages=messages,
        temperature=temperature,
    )


async def run_deep(
    messages: list[dict],
    lang: str = "en",
    temperature: float = 0.7,
    tier: Tier = Tier.GENERAL,
) -> AgentResult:
    """
    Compound deep synthesizer — groq/compound (DEEP_AGENT_MODEL).
    Higher quality synthesis. Used for SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE
    on Tier.GENERAL/HEAVY.
    tier is passed explicitly from coordinator — never hardcoded here (architecture.md §2.3).
    lang is accepted for interface compatibility but not passed to complete()
    (language is already enforced via system prompt in messages).
    """
    return await _run_compound(
        model=DEEP_AGENT_MODEL,
        tier=tier,
        messages=messages,
        temperature=temperature,
    )