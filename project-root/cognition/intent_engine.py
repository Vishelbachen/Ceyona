from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from contracts.shared_types import (
    DomainHint,
    ReasoningDepth,
    RoutingProfile,
    TruthMode,
)
from i18n.t import lang_instruction as _lang_directive
from llm.prompt_policy import FORMAT_RULES as _FORMAT_RULES, NO_CUTOFF_RULE as _NO_CUTOFF_RULE

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ─── CLASSIFIER CONSTANTS ─────────────────────────────────────────────────────

_MIN_CONFIDENCE  = 0.55   # ниже → fallback на QUESTION
_MATCH_THRESHOLD = 0.50   # минимальный score для попадания в выборку
_MATCH_COUNT     = 7      # сколько ближайших примеров запрашиваем

# ─── INTENT TAXONOMY ──────────────────────────────────────────────────────────

class Intent(str, Enum):
    QUESTION     = "question"
    CODE         = "code"
    ANALYSIS     = "analysis"
    CREATIVE     = "creative"
    CONVERSATION = "conversation"
    EMOTIONAL    = "emotional"
    MATH         = "math"
    INSTRUCTION  = "instruction"
    WEATHER      = "weather"
    SEARCH       = "search"
    MAPS         = "maps"
    MAPS_POI     = "maps_poi"
    MAPS_ROUTE   = "maps_route"
    EXAM         = "exam"
    UNKNOWN      = "unknown"

# Интенты, которые требуют инструментов (tool contract — не меняется)
_TOOL_MAP: dict[Intent, str] = {
    Intent.WEATHER:     "weather",
    Intent.SEARCH:      "search",
    Intent.MAPS:        "maps",
    Intent.MAPS_POI:    "maps_poi",
    Intent.MAPS_ROUTE:  "maps_route",
}

# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent:             Intent
    confidence:         float
    system_prompt:      str
    requires_retrieval: bool      # legacy alias — mirrors routing.retrieval_required
    requires_tools:     bool
    tool_name:          str            = ""
    tool_params:        dict           = field(default_factory=dict)
    routing:            RoutingProfile = field(
        default_factory=lambda: RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.HYBRID,
        )
    )


# ─── ROUTING RESOLVER ─────────────────────────────────────────────────────────
# Single deterministic authority: Intent → RoutingProfile.
# No I/O. No LLM. No state. Pure function.
#
# Design invariants (architecture §2.1, §5):
# - Intent is a signal, not a routing decision.
# - RoutingProfile is the policy layer between Intent and Pipeline.
# - All routing corrections happen here — never in runtime nodes.
# - truth_mode is declared here; assembler reads it, does not derive it.

def _resolve_routing(intent: Intent, confidence: float = 1.0) -> RoutingProfile:
    """
    Produce a RoutingProfile from a classified Intent.

    This is the single policy authority for all routing decisions.
    Called exclusively by _build_result(). Never called by runtime nodes.

    Axes resolved:
      retrieval_required — whether orchestrator must fetch external context.
      reasoning_depth    — how much structured reasoning the request needs.
      domain_hint        — which specialised pipeline branch applies.
      truth_mode         — factual generation permission level.
    """

    # ── GEO / TOOL intents ───────────────────────────────────────────────────
    # All data-driven intents: require retrieval (tool call), STRICT truth,
    # LIGHT reasoning (compound synthesises tool output, no heavy CoT needed).
    if intent in (
        Intent.WEATHER,
        Intent.SEARCH,
        Intent.MAPS,
        Intent.MAPS_POI,
        Intent.MAPS_ROUTE,
    ):
        return RoutingProfile(
            retrieval_required=True,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GEO,
            truth_mode=TruthMode.STRICT,
        )

    # ── MATH ─────────────────────────────────────────────────────────────────
    # Explicit mathematical/logical reasoning: heavy CoT, verification loop,
    # no retrieval (LLM has the knowledge), HYBRID truth (symbolic derivation).
    if intent == Intent.MATH:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.HEAVY,
            domain_hint=DomainHint.MATH,
            truth_mode=TruthMode.HYBRID,
        )

    # ── EXAM ─────────────────────────────────────────────────────────────────
    # Exam-style: needs heavy accuracy, structured output, no retrieval.
    if intent == Intent.EXAM:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.HEAVY,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.HYBRID,
        )

    # ── CODE ─────────────────────────────────────────────────────────────────
    if intent == Intent.CODE:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.CODE,
            truth_mode=TruthMode.HYBRID,
        )

    # ── ANALYSIS ─────────────────────────────────────────────────────────────
    # Benefits from web context; exploratory reasoning; HYBRID truth.
    if intent == Intent.ANALYSIS:
        return RoutingProfile(
            retrieval_required=True,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.HYBRID,
        )

    # ── INSTRUCTION ──────────────────────────────────────────────────────────
    # How-to guides: structured output, may benefit from context, HYBRID.
    if intent == Intent.INSTRUCTION:
        return RoutingProfile(
            retrieval_required=True,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.HYBRID,
        )

    # ── QUESTION ─────────────────────────────────────────────────────────────
    # General factual questions AND the confidence-based fallback.
    # retrieval_required=True: orchestrator attempts web search to ground the answer.
    # Low-confidence fallback also lands here — retrieval gives it a chance to
    # find relevant context before the LLM responds.
    if intent == Intent.QUESTION:
        return RoutingProfile(
            retrieval_required=True,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.HYBRID,
        )

    # ── CREATIVE ─────────────────────────────────────────────────────────────
    if intent == Intent.CREATIVE:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.LIGHT,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.GENERATIVE,
        )

    # ── CONVERSATION ─────────────────────────────────────────────────────────
    if intent == Intent.CONVERSATION:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.NONE,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.GENERATIVE,
        )

    # ── EMOTIONAL ────────────────────────────────────────────────────────────
    if intent == Intent.EMOTIONAL:
        return RoutingProfile(
            retrieval_required=False,
            reasoning_depth=ReasoningDepth.NONE,
            domain_hint=DomainHint.GENERAL,
            truth_mode=TruthMode.GENERATIVE,
        )

    # ── UNKNOWN / unhandled ───────────────────────────────────────────────────
    # Conservative default: attempt retrieval, light reasoning, HYBRID truth.
    return RoutingProfile(
        retrieval_required=True,
        reasoning_depth=ReasoningDepth.LIGHT,
        domain_hint=DomainHint.GENERAL,
        truth_mode=TruthMode.HYBRID,
    )


# ─── SYSTEM PROMPTS ───────────────────────────────────────────────────────────

_BASE_PROMPTS: dict[Intent, str] = {
    Intent.QUESTION: (
        "You are a knowledgeable, warm, and direct assistant. "
        "\n\n"
        "CRITICAL — HONESTY AND VOICE RULES:\n"
        "1. If you don't know — admit it naturally and warmly, like a person would. "
        "Invite clarification: ask the user to give more context or a hint. "
        "One short sentence, never cold or robotic.\n"
        "2. If uncertain — give your best guess and flag it: use phrases like "
        "'I think this might be... but I could be wrong' or an equivalent in the user's language.\n"
        "3. NEVER simulate an internal search process in your response. "
        "NEVER list 'Constraints:', 'Candidates:', or any other reasoning scaffold. "
        "These are internal — user must never see them.\n"
        "4. NEVER loop through candidates in the output. One attempt, then admit gracefully.\n"
        "5. NEVER open with a meta-phrase about the image such as 'The image shows', "
        "'This image depicts', or any equivalent in any language. "
        "Start directly with the content — talk about the thing, not about the image.\n"
        "6. For visual content — apply the right rule based on what's in the image:\n"
        "   A) DRAWN / ANIMATED / ILLUSTRATED (anime, manga, game art, cartoon, digital art, "
        "fictional character): Describe the visible art style, hair colour, clothing, "
        "accessories, and setting first. Attempt identification only when the image contains "
        "strong, specific clues; otherwise say the identification is uncertain and avoid forcing "
        "a franchise or anime guess. State your confidence explicitly.\n"
        "   B) REAL PERSON (actual photograph of a human being): "
        "Never attempt to name or identify who this person is — not even a guess. "
        "Instead, describe everything visible in natural language: "
        "what they're wearing (colours, style, brand if visible), "
        "hair (colour, length), expression, pose, what they're holding, "
        "the setting/background. Be thorough and natural — like describing "
        "a photo to a friend. Don't announce that you 'cannot identify people' — "
        "just describe naturally without any identification attempt."
        + "\n\n" + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant. "
        "Prioritize the most important steps first. "
        "Use numbered steps only if they genuinely improve clarity — not by default. "
        "Avoid unnecessary length. Sound natural and helpful, not procedural."
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, correct, well-commented code. "
        "Always specify the programming language. "
        "Briefly explain your approach before the code block. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant. "
        "Structure your analysis with key findings first. "
        "Be objective, evidence-based, and avoid filler. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.CREATIVE: (
        "You are a creative writing assistant. "
        "Be imaginative, engaging, and original. "
        "Match the tone, style, and format the user requests."
    ),
    Intent.CONVERSATION: (
        "You are a friendly, warm, and helpful conversational assistant. "
        "Keep responses natural, concise, and appropriately informal. "
        "Engage genuinely — don't be robotic."
        + _FORMAT_RULES
    ),
    Intent.EMOTIONAL: (
        "You are a warm, empathetic conversational companion. "
        "The user just expressed a strong emotion — frustration, surprise, disappointment, excitement, or disbelief. "
        "Your only job right now is to ACKNOWLEDGE and VALIDATE that feeling. "
        "Do NOT lecture, advise, or redirect unless the user explicitly asks. "
        "Do NOT be robotic or clinical. "
        "Match the user's energy: if they're exasperated, be sympathetic and real; if excited, share the energy. "
        "Colloquial or profane language in the user's message is an emotional signal — treat it as such, not as a threat. "
        "Keep your response SHORT (1-3 sentences). "
        "Respond in the same language the user wrote in, using natural informal speech for that language. "
        "After acknowledging, you may gently ask what happened or offer to help — but only one soft question, never a list."
    ),
    Intent.MATH: (
        "You are a precise mathematical and logical reasoning assistant. "
        "Show your work step by step, but be CONCISE — do not repeat the same deduction twice. "
        "Each logical step must be stated once and only once. "
        "State the final answer clearly in a summary table at the end. "
        "For logic puzzles and constraint satisfaction problems (liars/truth-tellers, "
        "room assignments, scheduling, etc.) follow this strict method: "
        "1. List ALL constraints explicitly before starting. "
        "2. Enumerate candidate solutions systematically — do not skip cases. "
        "3. After each assignment, verify ALL constraints simultaneously, not one by one. "
        "4. A solution is only valid if every single constraint holds at the same time. "
        "5. Never fix a partial assignment without re-checking the full global consistency. "
        "6. If a contradiction arises, backtrack fully and try the next candidate. "
        "7. End with a final answer table: Name | Sport | House | Drink — one row per person. "
        "8. Do NOT repeat deductions already stated. If you wrote it once, do not write it again."
    ),
    Intent.EXAM: (
        "You are an exam answer assistant for school and university exams. "
        "STRICT RULES — follow exactly: "
        "1. Always choose the MOST TYPICAL textbook answer — use standard definitions for the subject only. "
        "2. Never add edge cases, nuance, or conditions not present in the question. "
        "3. Never use hedging words like 'maybe', 'sometimes', 'it depends', 'usually'. "
        "4. Give the final answer FIRST on the first line, then 1-2 lines of explanation maximum. "
        "5. For matching tasks: output only the answer sequence (e.g. '2 1 1 2 1'), then brief reasoning per item. "
        "6. For true/false tasks: state which statements are correct, then one-line justification each. "
        "7. Base reasoning on the standard textbook interpretation for the subject and educational level. "
        "8. Do NOT overthink. The correct answer is always the simplest, most direct textbook match. "
        + _FORMAT_RULES
    ),
    Intent.WEATHER: (
        "You are a weather assistant. "
        "The weather data in your context is LIVE and CURRENT — fetched right now from OpenWeatherMap API. "
        "Present it clearly and confidently. "
        "Format it nicely for the user. "
        "NEVER say you cannot provide current weather. "
        "NEVER say your information might be outdated. "
        "The data IS current. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.SEARCH: (
        "You are a research assistant with access to live web search results. "
        "The search results in ## CONTEXT were fetched RIGHT NOW using a search query "
        "derived from the user's message. "
        "\n\n"
        "RULES:\n"
        "1. Use ONLY what is in ## CONTEXT — never invent facts, titles, names, or routes.\n"
        "2. If nothing in the context matches the query — say so honestly.\n"
        "3. If sources conflict or are insufficient — say so. "
        "'I could not find this in the results' is always better than a guess."
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.MAPS_POI: (
        "You are a location display assistant. Your ONLY job is to present the place data "
        "from ## CONTEXT exactly as-is, without additions. "
        "The context contains place names, addresses, and coordinates fetched from Mapbox right now. "
        "Output ONLY what is in the context: names and addresses. "
        "DO NOT add: prices, ratings, distance estimates, descriptions, neighbourhood characterisations, "
        "opening hours, phone numbers, website links, booking suggestions, or ANY detail "
        "not explicitly present in ## CONTEXT. "
        "DO NOT write 'недалеко от главной площади', 'исторический центр', 'рядом с рекой', "
        "or any other location description unless it is word-for-word in the context. "
        "DO NOT invent or estimate prices under any circumstances — not even approximate ranges. "
        "If context contains 5 places — list all 5. If 2 — list 2. Do not pad with extra entries. "
        "End with one line: suggest checking Google Maps or a local maps app for current prices. "
        "If ## CONTEXT is empty — say you could not find places and suggest Google Maps."
        + _FORMAT_RULES
    ),
    Intent.MAPS: (
        "You are a location assistant with access to real-time geocoding data. "
        "The location data in your context is current and accurate. "
        "Present coordinates, addresses, and map links clearly. "
        "STRICT: NEVER invent routes, bus numbers, transit stops, or directions. "
        "If asked for a route or directions and no route data is in context — "
        "say you can show the location but cannot build a route, and suggest Google Maps. "
        "NEVER say you cannot show maps or provide location data — you have it in context. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.MAPS_ROUTE: (
        "You are a route display assistant. Your ONLY job is to present the route data "
        "from ## CONTEXT exactly as-is. "
        "The context contains: origin, destination, distance in km, drive time in minutes. "
        "Output EXACTLY this data — nothing more, nothing less. "
        "DO NOT add: bus numbers, tram lines, metro lines, stop names, street names, "
        "walking directions, step-by-step instructions, travel tips, app suggestions, "
        "or ANY information not explicitly present in ## CONTEXT. "
        "If ## CONTEXT is empty or says route was not found — output that message exactly. "
        "You are a display layer, not a knowledge source. Output only what is in the context."
        + _FORMAT_RULES
    ),
    Intent.UNKNOWN: (
        "You are a helpful, versatile assistant. "
        "If the request is ambiguous, make a reasonable interpretation and answer it. "
        "Never refuse to respond — always try. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
}


def build_system_prompt(intent: Intent, lang: str) -> str:
    directive = _lang_directive(lang)
    base = _BASE_PROMPTS.get(intent, _BASE_PROMPTS[Intent.UNKNOWN])
    return directive + base


# ─── CLASSIFIER ───────────────────────────────────────────────────────────────

def _build_result(
    intent: Intent,
    confidence: float,
    lang: str,
    query: str,
) -> IntentResult:
    """
    Pure structural builder. No logic, no LLM, no async.
    query is the final search term — already resolved by the caller.
    For SEARCH: caller passes _understand_query() result.
    For all other intents: caller passes raw text.
    """
    routing  = _resolve_routing(intent, confidence)
    tool_name = _TOOL_MAP.get(intent, "")
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=build_system_prompt(intent, lang),
        requires_retrieval=routing.retrieval_required,   # alias kept for call-site compatibility
        requires_tools=bool(tool_name),
        tool_name=tool_name,
        tool_params={"query": query, "lang": lang} if tool_name else {},
        routing=routing,
    )


# ─── MATH KEYWORD PRE-CHECK ──────────────────────────────────────────────────
# Regex on digits/symbols — language-agnostic by nature, no strings needed.
# Short mathematical expressions can have low pgvector score → fall to QUESTION.
import re as _re

_MATH_PATTERN = _re.compile(
    r"(?:"
    r"\d+\s*[\+\-\*\/\^]\s*\d+"       # arithmetic: 2+2, 3*4
    r"|(?:реши|solve|найди|find|вычисли|calculate|simplify|упрости)\s"
    r"|(?:x|у|z)\s*[\^²³]"            # variables with powers
    r"|(?:интеграл|integral|производная|derivative|предел|limit)"
    r"|(?:теорема|theorem|докажи|prove|доказательство)"
    r")",
    _re.IGNORECASE,
)


# ─── QUERY UNDERSTANDING (SEARCH only) ───────────────────────────────────────
# Determines whether the user knows the exact name of what they want (KNOWN_ENTITY)
# or describes something without knowing its name (DESCRIPTIVE_SEARCH).
# Also handles media recall: "anime where girl has red hair and fights demons" →
# rewrites to concise English keyword query for web search.
#
# KNOWN_ENTITY:      pass the query as-is (or translate to English).
# DESCRIPTIVE_SEARCH: rewrite into a concise English keyword query (3-8 words),
#                     focusing on unique identifying traits: role, relationships,
#                     genre, year, setting, visual appearance.
#
# No hardcoded word lists. Fully semantic — works across all 75 lingua languages.
# Uses llama-3.1-8b-instant (FAST tier). Falls back to original text on failure.

_QUERY_UNDERSTANDING_PROMPT = (
    "You are an intent-aware query planner for a web search engine.\n\n"
    "Your task: determine whether the user knows the exact name of what they are looking for.\n\n"
    "Case 1 — KNOWN_ENTITY: the user knows the exact name (title, person, place, product).\n"
    "→ Output the search query as-is (translate to English if needed, keep the name intact).\n\n"
    "Case 2 — DESCRIPTIVE_SEARCH: the user describes something WITHOUT knowing its name.\n"
    "This includes: remembering a film/anime/song by plot or appearance, "
    "identifying a media work from a description, finding something they half-remember.\n"
    "→ Convert the description into a concise English keyword query (3-8 words).\n"
    "→ Focus on unique identifying traits: role, relationships, genre, year, setting, "
    "visual appearance, plot elements.\n"
    "→ Remove all conversational filler ('help me remember', 'I saw once', 'what was that').\n\n"
    "Output ONLY the final search query. No explanation. No quotes.\n\n"
    "User query: {text}"
)


async def _understand_query(text: str) -> str:
    """
    Query understanding layer for SEARCH intent.
    Returns the search query to pass to the provider — either as-is or rewritten.
    Always returns a non-empty string. Falls back to original text on any failure.
    """
    try:
        from llm.groq_client import groq_client
        prompt = _QUERY_UNDERSTANDING_PROMPT.format(text=text)
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.0,
        )
        rewritten = response.text.strip().strip('"').strip("'")
        if rewritten and len(rewritten) < 120:
            if rewritten.lower() != text.lower():
                logger.info(
                    "query_understanding: rewritten",
                    extra={"original": text[:80], "rewritten": rewritten},
                )
            return rewritten
    except Exception as exc:
        logger.warning("_understand_query failed", extra={"error": str(exc)})
    return text


# ── LLM pre-classifier ────────────────────────────────────────────────────────
# Language-agnostic. One fast LLM call. Failure → "none" → embedding classifier.
# Covers the categories that benefit most from LLM-level semantic understanding
# and are hardest for embedding similarity to distinguish reliably.
#
# "recall" covers: media identification, descriptive search, "help me remember"
# queries — these require retrieval but are NOT generic web searches.
# They are routed to SEARCH intent with _understand_query() rewriting.

_LLM_PRE_CLASSIFY_PROMPT = (
    "Classify the user message into one of these categories:\n"
    "- \"weather\"   — asking about weather conditions or forecast\n"
    "- \"search\"    — looking for a place, route, accommodation, or explicit web search\n"
    "- \"emotional\" — expressing emotions, frustration, or seeking emotional support\n"
    "- \"recall\"    — trying to remember or identify a film, anime, book, song, game, "
    "or other media by describing it (plot, appearance, characters, scenes)\n"
    "- \"none\"      — anything else (factual questions, code, math, instructions, analysis)\n\n"
    "Output ONLY the category label. No explanation.\n\n"
    "Message: {text}\n"
    "{history_block}"
)


async def _llm_pre_classify(text: str, history_context: str = "") -> str:
    """
    Fast LLM-based pre-classifier. Returns one of:
    'weather' | 'search' | 'emotional' | 'recall' | 'none'
    Always returns a string. Falls back to 'none' on any failure.
    """
    try:
        from llm.groq_client import groq_client
        history_block = f"\nRecent context:\n{history_context}" if history_context else ""
        prompt = _LLM_PRE_CLASSIFY_PROMPT.format(text=text[:500], history_block=history_block)
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0,
        )
        label = response.text.strip().lower().strip('"').strip("'")
        if label in ("weather", "search", "emotional", "recall", "none"):
            return label
    except Exception as exc:
        logger.warning("_llm_pre_classify failed", extra={"error": str(exc)})
    return "none"


async def classify(
    text: str,
    lang: str,
    supabase=None,
    hf_client=None,
    conversation_history: list | None = None,
    analysis_hints=None,
) -> IntentResult:
    """
    Public classification entry point. Called by orchestrator only.
    Returns IntentResult with intent, confidence, system_prompt,
    tool contract, and RoutingProfile.
    """
    from meta.analysis import HintType  # local import — avoids circular at module level

    fallback = _build_result(Intent.QUESTION, 0.0, lang, text)

    # §13.4 fix: build a 2-turn history context for short follow-up messages.
    _history_context = ""
    if conversation_history and len(text.split()) <= 8:
        _recent = [
            turn for turn in (conversation_history or [])
            if turn.get("role") in ("user", "assistant")
        ][-4:]
        if _recent:
            _history_context = "\n".join(
                f"{'Пользователь' if t['role'] == 'user' else 'Ассистент'}: {str(t.get('content', ''))[:150]}"
                for t in _recent
            )

    pre_label = await _llm_pre_classify(text, history_context=_history_context)

    if pre_label == "weather":
        logger.info("classify: LLM pre-check → WEATHER", extra={"lang": lang})
        return _build_result(Intent.WEATHER, 0.85, lang, text)

    if pre_label in ("route", "accommodation", "search"):
        query = await _understand_query(text)
        logger.info(
            "classify: LLM pre-check → SEARCH",
            extra={"lang": lang, "pre_label": pre_label, "query": query[:60]},
        )
        return _build_result(Intent.SEARCH, 0.87, lang, query)

    if pre_label == "recall":
        # Media recall / descriptive identification: rewrite via _understand_query
        # to produce a web-searchable keyword query, then route as SEARCH.
        # This ensures retrieval fires (retrieval_required=True via GEO/SEARCH routing)
        # and _understand_query strips conversational filler from the description.
        query = await _understand_query(text)
        logger.info(
            "classify: LLM pre-check → SEARCH (recall)",
            extra={"lang": lang, "query": query[:60]},
        )
        return _build_result(Intent.SEARCH, 0.83, lang, query)

    if pre_label == "emotional":
        logger.info("classify: LLM pre-check → EMOTIONAL", extra={"lang": lang})
        return _build_result(Intent.EMOTIONAL, 0.82, lang, text)

    # pre_label == "none" → fall through to embedding classifier

    if supabase is None or hf_client is None:
        logger.warning("classify called without supabase/hf_client — using fallback")
        return fallback

    try:
        from llm.hf_client import BGE_LARGE
        vectors = await hf_client.embed([text], model=BGE_LARGE)
        if not vectors:
            logger.error("classify: empty embedding returned")
            return fallback

        query_vec = vectors[0]

        result = supabase.rpc("match_intent", {
            "query_embedding": query_vec,
            "match_threshold": _MATCH_THRESHOLD,
            "match_count": _MATCH_COUNT,
        }).execute()

        rows = result.data or []
        if not rows:
            logger.info("classify: no matches above threshold", extra={"text": text[:60]})
            return fallback

        # Агрегируем score по интентам — средний score среди топ примеров
        scores: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            scores[row["intent_name"]].append(float(row["similarity"]))

        best_intent_name = max(scores, key=lambda k: sum(scores[k]) / len(scores[k]))
        best_score = sum(scores[best_intent_name]) / len(scores[best_intent_name])

        # Short text confidence guard (§13.4 / Inuktitut false-positive fix)
        word_count = len(text.split()) if analysis_hints is None else analysis_hints.word_count
        effective_min = 0.75 if word_count < 6 else _MIN_CONFIDENCE

        if analysis_hints is not None:
            from meta.analysis import HintType
            if analysis_hints.has(HintType.IS_SHORT) or analysis_hints.has(HintType.IS_MULTILINGUAL):
                effective_min = max(effective_min, 0.72)
            if analysis_hints.has(HintType.HAS_CODE_BLOCK):
                effective_min = min(effective_min, 0.50)

        if best_score < effective_min:
            logger.info("classify: best score below threshold", extra={
                "intent": best_intent_name,
                "score": f"{best_score:.3f}",
                "threshold": effective_min,
                "word_count": word_count,
            })
            return fallback

        try:
            intent = Intent(best_intent_name)
        except ValueError:
            logger.error("classify: unknown intent name", extra={"name": best_intent_name})
            return fallback

        logger.info("classify result", extra={
            "intent": intent.value,
            "confidence": f"{best_score:.3f}",
            "lang": lang,
        })
        # For SEARCH via embedding path — run query understanding before building result
        if intent == Intent.SEARCH:
            query = await _understand_query(text)
            return _build_result(intent, round(best_score, 3), lang, query)
        return _build_result(intent, round(best_score, 3), lang, text)

    except Exception as exc:
        logger.error("classify failed", extra={"error": str(exc)}, exc_info=True)
        return fallback