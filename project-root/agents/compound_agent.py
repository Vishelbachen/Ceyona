from __future__ import annotations

"""
Compound Agent — tool-use execution fabric.

Wraps groq/compound (deep) and groq/compound-mini (fast) via the Groq
tool-use API.  Compound models MUST receive a `tools` parameter — calling
them as plain chat-completion returns an empty response (architecture.md §27).

Architecture contract:
  - No policy authority.  No model selection.  No routing decisions.
  - Receives intent + lang from coordinator; executes tool loop; returns AgentResult.
  - Tool execution delegates to existing external service singletons
    (search_service, weather_service, maps_service).
  - Max tool rounds: _MAX_TOOL_ROUNDS (bounded — no unbounded loops, §2.2).
  - On any failure: returns AgentResult(success=False) — coordinator handles fallback.

Supported tools:
  web_search  → external.search.SearchService.search()
  get_weather → external.weather.WeatherService.get_current()
  geocode     → external.maps.MapsService.geocode()
  get_route   → external.maps.MapsService.get_route()
  get_route   → external.maps.MapsService.get_route()
"""

import json
import logging

from agents.fast_agent import AgentResult
from contracts.shared_types import Tier
from external.maps import maps_service
from external.search import search_service
from external.weather import weather_service
from llm.groq_client import LLMResponse, ToolCallResponse, groq_client
from llm.model_router import DEEP_AGENT_MODEL, FAST_AGENT_MODEL, route_max_tokens

logger = logging.getLogger(__name__)

# Bounded tool execution loop — architecture §2.2 (no unbounded retry loops)
_MAX_TOOL_ROUNDS = 3


# ─── TOOL SCHEMAS (Groq function-calling format) ──────────────────────────────

_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information. "
                "Use for: news, facts, prices, schedules, availability, "
                "current events, and any information that changes over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Be specific and use the user's language.",
                    },
                    "lang": {
                        "type": "string",
                        "description": "BCP-47 language code for results (e.g. 'en', 'ru', 'ar').",
                        "default": "en",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current weather for a city. "
                "Use only for explicit weather requests — temperature, conditions, forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name in English or local language.",
                    },
                    "lang": {
                        "type": "string",
                        "description": "BCP-47 language code for the response.",
                        "default": "en",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": (
                "Look up a place, address, or point of interest on a map. "
                "Use for: finding locations, getting coordinates, verifying addresses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Place name or address to look up.",
                    },
                    "lang": {
                        "type": "string",
                        "description": "BCP-47 language code for the response.",
                        "default": "en",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": (
                "Get driving directions and route info between two places. "
                "Use for: 'how to get from X to Y', distance, travel time, route planning."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": (
                            "Starting point — full geocodable place name "
                            "(e.g. 'Moscow Kremlin', 'Voronezh train station'). "
                            "Never use vague terms like 'center' or 'station' without the city name."
                        ),
                    },
                    "destination": {
                        "type": "string",
                        "description": (
                            "Destination — full geocodable place name. "
                            "Include city name always."
                        ),
                    },
                    "lang": {
                        "type": "string",
                        "description": "BCP-47 language code for the response.",
                        "default": "en",
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
]


# ─── TOOL EXECUTION ───────────────────────────────────────────────────────────

async def _execute_tool(name: str, arguments: str, lang: str) -> str:
    """
    Execute a single tool call and return a plain-text result string.

    Never raises — returns an error string on failure so the model
    can reason about the failure and still produce a useful response.
    """
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as exc:
        logger.error("compound_agent: tool argument JSON parse failed",
                     extra={"tool": name, "error": str(exc)})
        return f"[tool error: could not parse arguments — {exc}]"

    try:
        if name == "web_search":
            query    = args.get("query", "")
            req_lang = args.get("lang", lang)
            results  = await search_service.search(query=query, lang=req_lang)
            if not results:
                return "[web_search: no results found]"
            return search_service.format_results(results, lang=req_lang)

        if name == "get_weather":
            city     = args.get("city", "")
            req_lang = args.get("lang", lang)
            data     = await weather_service.get_current(city=city, lang=req_lang)
            if data is None:
                return f"[get_weather: could not retrieve weather for '{city}']"
            return weather_service.format_current(data, lang=req_lang)

        if name == "geocode":
            query    = args.get("query", "")
            req_lang = args.get("lang", lang)
            feature  = await maps_service.geocode(query=query, lang=req_lang)
            if feature is None:
                return f"[geocode: location not found for '{query}']"
            return maps_service.format_geocode(feature, lang=req_lang)

        if name == "get_route":
            origin      = args.get("origin", "")
            destination = args.get("destination", "")
            req_lang    = args.get("lang", lang)
            if not origin or not destination:
                return "[get_route: origin and destination are required]"
            route = await maps_service.get_route(
                origin=origin, destination=destination, lang=req_lang
            )
            if route is None:
                return maps_service.format_route_not_found(req_lang)
            return maps_service.format_route(route, lang=req_lang)

        logger.warning("compound_agent: unknown tool requested",
                       extra={"tool": name})
        return f"[tool error: unknown tool '{name}']"

    except Exception as exc:
        logger.error("compound_agent: tool execution failed",
                     extra={"tool": name, "error": str(exc)})
        return f"[tool error: {name} failed — {exc}]"


# ─── TOOL MESSAGE BUILDER ─────────────────────────────────────────────────────

def _build_tool_result_messages(
    assistant_raw_message: dict,
    tool_results: list[tuple[str, str]],  # [(tool_call_id, result_text)]
) -> list[dict]:
    """
    Build the assistant + tool result messages to append to conversation history.

    Groq tool-use protocol requires:
      1. The assistant message that requested the tools (with tool_calls field).
      2. One "tool" role message per tool call, with matching tool_call_id.
    """
    messages = [assistant_raw_message]
    for tool_call_id, result_text in tool_results:
        messages.append({
            "role":         "tool",
            "tool_call_id": tool_call_id,
            "content":      result_text,
        })
    return messages


# ─── MAIN ENTRY POINTS ────────────────────────────────────────────────────────

async def _run_compound(
    model: str,
    tier: Tier,
    messages: list[dict],
    lang: str,
    temperature: float,
) -> AgentResult:
    """
    Execute the compound model tool-use loop.

    Loop (bounded by _MAX_TOOL_ROUNDS):
      1. Call model with tools.
      2. If ToolCallResponse → execute tools → append results → repeat.
      3. If LLMResponse → return text.
      4. If max rounds exceeded → return failure.
    """
    current_messages = list(messages)
    max_tokens = route_max_tokens(tier)

    total_input_tokens  = 0
    total_output_tokens = 0
    total_tool_calls    = 0  # compound tool calls executed — billing counter

    for round_num in range(_MAX_TOOL_ROUNDS + 1):
        try:
            result = await groq_client.complete_with_tools(
                model=model,
                messages=current_messages,
                tools=_TOOL_SCHEMAS,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            # Log full error so we can diagnose compound model availability issues
            # (e.g. groq/compound-mini 404, API key issues, rate limits)
            logger.error(
                "compound_agent: API call failed",
                extra={
                    "model":  model,
                    "round":  round_num,
                    "error":  str(exc),
                    "type":   type(exc).__name__,
                },
            )
            return AgentResult(
                text="", model=model, input_tokens=total_input_tokens,
                output_tokens=total_output_tokens, success=False, error=str(exc),
                tool_calls=total_tool_calls,
            )

        total_input_tokens  += result.input_tokens
        total_output_tokens += result.output_tokens

        # Model produced a final text answer
        if isinstance(result, LLMResponse):
            return AgentResult(
                text=result.text,
                model=result.model,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                success=bool(result.text.strip()),
                tool_calls=total_tool_calls,
            )

        # Model requested tool calls
        if isinstance(result, ToolCallResponse):
            if round_num >= _MAX_TOOL_ROUNDS:
                logger.warning(
                    "compound_agent: max tool rounds reached — returning empty",
                    extra={"model": model, "rounds": round_num},
                )
                return AgentResult(
                    text="", model=model, input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens, success=False,
                    error=f"max_tool_rounds_exceeded ({_MAX_TOOL_ROUNDS})",
                    tool_calls=total_tool_calls,
                )

            logger.info(
                "compound_agent: executing tool calls",
                extra={
                    "model":  model,
                    "round":  round_num,
                    "tools":  [tc.name for tc in result.tool_calls],
                },
            )

            # Execute all requested tools
            tool_results: list[tuple[str, str]] = []
            for tc in result.tool_calls:
                tool_text = await _execute_tool(tc.name, tc.arguments, lang)
                tool_results.append((tc.id, tool_text))
            total_tool_calls += len(result.tool_calls)  # billing: count each call

            # Append assistant message + tool results to conversation
            tool_messages = _build_tool_result_messages(
                result.raw_message, tool_results
            )
            current_messages = current_messages + tool_messages
            continue

        # Unexpected return type — defensive
        logger.error(
            "compound_agent: unexpected result type",
            extra={"type": type(result).__name__},
        )
        return AgentResult(
            text="", model=model, input_tokens=total_input_tokens,
            output_tokens=total_output_tokens, success=False,
            error="unexpected_result_type",
            tool_calls=total_tool_calls,
        )

    # Should be unreachable — loop exits via return inside
    return AgentResult(
        text="", model=model, input_tokens=total_input_tokens,
        output_tokens=total_output_tokens, success=False,
        error="loop_exhausted",
        tool_calls=total_tool_calls,
    )


async def run_fast(messages: list[dict], lang: str = "en", temperature: float = 0.7) -> AgentResult:
    """
    Compound fast agent — groq/compound-mini (FAST_AGENT_MODEL).
    Single-step tool use, low latency.
    Used for: SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE intents on Tier.FAST path.
    """
    return await _run_compound(
        model=FAST_AGENT_MODEL,
        tier=Tier.FAST,
        messages=messages,
        lang=lang,
        temperature=temperature,
    )


async def run_deep(messages: list[dict], lang: str = "en", temperature: float = 0.7) -> AgentResult:
    """
    Compound deep agent — groq/compound (DEEP_AGENT_MODEL).
    Multi-step tool use, deeper reasoning.
    Used for: SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE intents on Tier.GENERAL/HEAVY path.
    """
    return await _run_compound(
        model=DEEP_AGENT_MODEL,
        tier=Tier.GENERAL,
        messages=messages,
        lang=lang,
        temperature=temperature,
    )