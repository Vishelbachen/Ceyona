from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from i18n.t import lang_instruction as _lang_directive

if TYPE_CHECKING:
    from meta.analysis import AnalysisReport

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

# Интенты, которые требуют инструментов
_TOOL_MAP: dict[Intent, str] = {
    Intent.WEATHER:     "weather",
    Intent.SEARCH:      "search",
    Intent.MAPS:        "maps",
    Intent.MAPS_POI:    "maps_poi",
    Intent.MAPS_ROUTE:  "maps_route",
}

# Интенты, которые требуют retrieval
_NEEDS_RETRIEVAL: frozenset[Intent] = frozenset({
    Intent.QUESTION,
    Intent.ANALYSIS,
    Intent.INSTRUCTION,
    Intent.SEARCH,
})

# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent:             Intent
    confidence:         float
    system_prompt:      str
    requires_retrieval: bool
    requires_tools:     bool
    tool_name:          str  = ""
    tool_params:        dict = field(default_factory=dict)


# ─── SYSTEM PROMPTS ───────────────────────────────────────────────────────────

_NO_CUTOFF = (
    "ABSOLUTE RULE: You have access to live web search results fetched RIGHT NOW. "
    "NEVER say your information is outdated, has a cutoff date, or may not be current. "
    "NEVER use: 'as of my last update', 'I cannot access real-time data', "
    "'my knowledge cutoff', 'this may have changed', 'I don't have current info'. "
    "The CONTEXT section contains live data — treat it as fully current. "
    "If context is present, use it. If absent, answer from general knowledge without disclaimers."
)

_FORMAT_RULES = (
    "FORMATTING — mandatory: "
    "Never use Markdown tables (no | pipes |). "
    "Never use Markdown headers (no ###, ##, #). "
    "Never open with filler phrases like 'Of course!', 'Sure!', 'Great question!', "
    "'Похоже', 'Давайте', 'Конечно!', 'Certainly!', 'Absolutely!'. "
    "Go straight to the answer with no preamble. "
    "Use plain text, numbered lists, or dashes only. "
)

_BASE_PROMPTS: dict[Intent, str] = {
    Intent.QUESTION: (
        "You are a knowledgeable and direct assistant. "
        "You have access to real-time web search results provided in the context. "
        "Use the provided context to answer accurately. "
        "If context is provided, base your answer on it — do not contradict it. "
        "\n\n"
        "CRITICAL — HONESTY AND GRACEFUL EXIT RULES:\n"
        "1. If you don't know the answer — say so directly in one sentence. "
        "Example: 'Я не знаю, кто этот персонаж.' or 'I'm not sure about this.' "
        "This is always better than guessing or simulating a search.\n"
        "2. If you're not certain — state your best guess and flag it explicitly: "
        "'Не уверена, но похоже это...' / 'I think this might be... but I'm not sure.'\n"
        "3. NEVER simulate an internal search process in your response. "
        "NEVER list 'Constraints:', 'Candidates:', 'Ограничения:', 'Кандидаты:' "
        "or any other reasoning scaffold in the final answer. "
        "These are internal steps — the user must never see them.\n"
        "4. NEVER loop through candidates in the output. "
        "If you can't find the answer after one attempt — admit it directly.\n"
        "5. For visual recognition tasks — CHECK FIRST what type of image it is:\\n"
        "   A) DRAWN / ANIMATED / ILLUSTRATED (anime, manga, game art, cartoon, digital art): "
        "ALWAYS attempt to identify — describe art style, clothing, hair color, accessories, setting, "
        "and make your best guess with explicit reasoning. "
        "Example: 'Судя по стилю арта и синим волосам, это похоже на Bronya из Honkai: Star Rail. "
        "Уточни, если ошибаюсь.' "
        "Only say you don't know if you have genuinely zero visual clues. "
        "Uncertainty is fine — always try first.\\n"
        "   B) REAL PERSON (photograph of an actual human being): "
        "Do NOT attempt to identify who this person is. "
        "Instead IMMEDIATELY and MANDATORILY describe everything visible: "
        "clothing, colours, setting, objects, actions, context, mood — all visual details. "
        "The description is NOT optional — it is the required response. "
        "Start with: 'Я не идентифицирую людей по фото, но вот что вижу:' (or equivalent in user's language), "
        "then describe fully."
        + "\n\n" + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant specialising in step-by-step guidance. "
        "Provide clear, numbered instructions. "
        "Be complete but concise. Start directly with step 1. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, correct, well-commented code. "
        "Always specify the programming language. "
        "Briefly explain your approach before the code block. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant with access to real-time web data provided in context. "
        "Structure your analysis with key findings first. "
        "Base your analysis on the provided context where available. "
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
    Intent.EXAM: ("You are an exam answer assistant for school exams (OGE, EGE, VPR and equivalents). "
        "STRICT RULES — follow exactly: "
        "1. Always choose the MOST TYPICAL textbook answer — use standard school definitions only. "
        "2. Never add edge cases, nuance, or conditions not present in the question. "
        "3. Never use hedging words like 'maybe', 'sometimes', 'it depends', 'usually'. "
        "4. Give the final answer FIRST on the first line, then 1-2 lines of explanation maximum. "
        "5. For matching tasks: output only the answer sequence (e.g. '2 1 1 2 1'), then brief reasoning per item. "
        "6. For true/false tasks: state which statements are correct, then one-line justification each. "
        "7. Base reasoning on the most common school textbook interpretation for the subject. "
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
        "The search results in your context were fetched from the web RIGHT NOW. "
        "NEVER say you cannot search or that your data is outdated — you have live results. "
        "NEVER make up information — only use what is in the context. "
        "\n\n"
        "SEARCH QUERY REFORMULATION (mandatory — do this before every search call):\n"
        "If the user describes something (anime plot, book description, event, product, person) "
        "without naming it — DO NOT search using the user's raw words verbatim. "
        "Instead reformulate into a SHORT English keyword query (3-6 words max). "
        "Examples: 'аниме где якудза охраняет дочь' → 'yakuza bodyguard daughter anime'; "
        "'фильм корабль тонет начало 20 века' → 'Titanic 1997'; "
        "'дешёвые отели Нью-Йорк' → 'budget hotels New York'.\n"
        "Use English for all title/factual searches. Use the original language only for "
        "local-service queries (hotels, restaurants in a specific city).\n"
        "You have 3 search rounds — if the first fails, try a DIFFERENT query reformulation "
        "(different keywords, more specific, or add year/country).\n"
        "\n\n"
        "HOW TO ANSWER:\n"
        "1. Read ALL search results in ## CONTEXT carefully.\n"
        "2. Synthesise the information into a direct, useful answer — do NOT copy-paste snippets.\n"
        "3. For navigation/route queries: "
        "CRITICAL — if the sources do not explicitly name a specific bus number, tram, "
        "metro line, or stop — do NOT invent one. Not even a plausible-sounding one. "
        "Instead say: 'For exact bus numbers and schedules, check Yandex.Transport or 2GIS.' "
        "Only mention a route number if a source in ## CONTEXT explicitly states it. "
        "Example of what NOT to do: 'Bus 27A departs from ul. Perkhorovicha' — "
        "if that is not in the context, it is hallucination. Do not do this.\n"
        "4. For hotel/accommodation queries: only name hotels that appear in the sources. "
        "Do not add hotels from general knowledge. "
        "Mention the source number (e.g. 'source 2') so the user can verify.\n"
        "5. For factual queries: give a concise answer, cite the most reliable source.\n"
        "6. Filter out SEO junk — if a source is clearly low-quality or irrelevant, ignore it.\n"
        "7. End with 1-2 most useful links if they add value. "
        "Never list all sources mechanically. Never include links that contain "
        "garbled characters or non-ASCII symbols in the URL path.\n"
        "8. If sources conflict or are insufficient, say so honestly and briefly. "
        "It is always better to say 'I could not find this detail in the sources' "
        "than to invent a specific fact."
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
        "End with one line: suggest checking Booking.com/2GIS/Google Maps for current prices. "
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
        "You have access to real-time web search results in your context. "
        "Use the context to answer accurately. "
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
    text: str,
) -> IntentResult:
    tool_name = _TOOL_MAP.get(intent, "")
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=build_system_prompt(intent, lang),
        requires_retrieval=intent in _NEEDS_RETRIEVAL,
        requires_tools=bool(tool_name),
        tool_name=tool_name,
        tool_params={"query": text, "lang": lang} if tool_name else {},
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


# ─── LLM PRE-CLASSIFIER ──────────────────────────────────────────────────────
# Replaces all hardcoded signal tuples (_WEATHER_SIGNALS, _ROUTE_SIGNALS,
# _ACCOMMODATION_SIGNALS, _EMOTIONAL_SIGNALS).
#
# WHY: signal tuples are hardcoded per language. With 75 languages (lingua),
# full coverage is impossible — any uncovered language causes misclassification.
# LLM understands semantics in all languages without any language-specific strings.
#
# MODEL: llama-3.1-8b-instant (FAST tier) — low latency, called once per request.
# POSITION: before embedding classifier, after math regex pre-check.
#
# Returns one of:
#   "weather"       → Intent.WEATHER
#   "route"         → Intent.SEARCH  (transit info, not Mapbox driving)
#   "accommodation" → Intent.SEARCH  (anti-hallucination: only SerpAPI sources)
#   "emotional"     → Intent.EMOTIONAL
#   "none"          → proceed to embedding classifier
#
# Failure policy: any exception or unexpected response → "none" (pass through).
# Never blocks the pipeline. Pre-check is best-effort, not authoritative.

_PRE_CLASSIFIER_PROMPT = (
    "Classify the intent of the following user message. "
    "Reply with a JSON object ONLY — no markdown, no explanation:\n"
    '{{"pre_intent": "<label>"}}\n\n'
    "Labels (choose exactly one):\n"
    "- \"weather\"       — asks about current weather, temperature, forecast, "
    "wind, humidity, precipitation for any location\n"
    "- \"route\"         — asks how to travel FROM one place TO another: "
    "directions, transit options, bus/metro/train/taxi routes, travel time, "
    "distance between two specific points, how to get from airport/station\n"
    "- \"accommodation\" — asks about hotels, hostels, motels, guesthouses, "
    "apartments, where to stay, cheap/budget/luxury lodging in a specific city\n"
    "- \"search\"        — asks to find, look up, search for specific current "
    "information: news, events, people, places, products, anime/film/book titles, "
    "recommendations, anything needing a web search for up-to-date facts\n"
    "- \"emotional\"     — expresses a strong emotion with no information request: "
    "surprise, frustration, excitement, disappointment, profanity, exclamations\n"
    "- \"none\"          — everything else: code, math, general chat, "
    "instructions, analysis, abstract questions answerable from knowledge\n\n"
    "CRITICAL: reply with JSON only. No text before or after.\n\n"
    "Message: {text}"
)

async def _llm_pre_classify(text: str, history_context: str = "") -> str:
    """
    Run LLM pre-classification on the user message.
    Returns one of: "weather", "route", "accommodation", "emotional", "search", "none".
    Always returns "none" on any failure — never raises.

    history_context: last 2-3 turns summary passed from classify() (audit §13.4).
    Allows classifier to resolve follow-up messages like "Вот, нашла" or "Туговатый поиск)"
    that are meaningless without prior conversation context.
    """
    import json

    from llm.groq_client import (
        groq_client,  # module-level singleton, safe to import here
    )
    try:
        # Build prompt with optional history context prefix (§13.4)
        if history_context:
            prompt_text = (
                f"[Предыдущий контекст разговора (последние реплики):\n{history_context}]\n\n"
                f"Текущее сообщение: {text[:400]}"
            )
        else:
            prompt_text = text[:500]

        prompt = _PRE_CLASSIFIER_PROMPT.format(text=prompt_text)
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.0,
        )
        raw = response.text.strip()
        # Strip markdown code fences if model wrapped the JSON
        if raw.startswith("```"):
            raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        # Model sometimes returns escaped key like '\"pre_intent\"' — normalize all keys
        data = {k.strip().strip('"').strip("'"): v for k, v in data.items()}
        label = data.get("pre_intent", "none").strip().lower()
        if label in {"weather", "route", "accommodation", "emotional", "search", "none"}:
            logger.info(
                "_llm_pre_classify: ok",
                extra={"label": label, "text_preview": text[:60]},
            )
            return label
        logger.warning(
            "_llm_pre_classify: unexpected label — defaulting to none",
            extra={"label": label, "text_preview": text[:60]},
        )
        return "none"
    except json.JSONDecodeError as exc:
        logger.warning(
            "_llm_pre_classify: JSON parse failed — passing through to embedding classifier",
            extra={
                "error": str(exc),
                "raw_response": response.text[:120] if "response" in dir() else "no_response",
                "text_preview": text[:60],
            },
        )
        return "none"
    except Exception as exc:
        logger.warning(
            "_llm_pre_classify: failed — passing through to embedding classifier",
            extra={
                "error": str(exc),
                "error_type": type(exc).__name__,
                "text_preview": text[:60],
            },
            exc_info=True,
        )
        return "none"


async def classify(
    text: str,
    lang: str = "en",
    supabase=None,
    hf_client=None,
    conversation_history: list[dict] | None = None,
    analysis_hints: "AnalysisReport | None" = None,
) -> IntentResult:
    """
    Classify user intent via BGE embedding + Supabase pgvector similarity.

    Falls back to Intent.QUESTION if:
      - supabase or hf_client not provided
      - embedding fails
      - no match above MIN_CONFIDENCE

    analysis_hints: optional AnalysisReport from meta/analysis.py (pre-reasoning hints).
    Non-binding — used to boost confidence for structurally clear intents and to
    adjust effective_min threshold for short/multilingual input.
    analysis_hints is never authoritative — it only adjusts probabilities.
    """
    from meta.analysis import HintType
    fallback = _build_result(Intent.QUESTION, 0.70, lang, text)

    # ── analysis_hints: math boost (structural signal, no I/O cost) ──────────
    # If analysis detected HAS_MATH with high confidence → skip LLM pre-classifier
    # and go straight to MATH intent. Faster and more reliable than regex alone.
    if analysis_hints is not None and analysis_hints.has(HintType.HAS_MATH):
        hint = analysis_hints.get(HintType.HAS_MATH)
        if hint and hint.confidence >= 0.80:
            logger.info(
                "classify: analysis_hints HAS_MATH → MATH (skipping LLM pre-check)",
                extra={"lang": lang, "confidence": hint.confidence},
            )
            return _build_result(Intent.MATH, 0.87, lang, text)

    # ── math pre-check (language-agnostic regex) ──────────────────────────────
    # Runs before LLM pre-classifier: regex is instant, no I/O cost.
    if _MATH_PATTERN.search(text):
        logger.info("classify: math regex pre-check → MATH", extra={"lang": lang})
        return _build_result(Intent.MATH, 0.85, lang, text)

    # ── LLM pre-classifier (language-agnostic, all 75 lingua languages) ───────
    # Replaces hardcoded signal tuples. One fast LLM call covers any language.
    # Failure → "none" → falls through to embedding classifier (never blocks).
    #
    # §13.4 fix: build a 2-turn history context for short follow-up messages.
    # "Вот, нашла" / "Туговатый поиск)" — meaningless without prior context.
    # We pass last 2 assistant turns (not user — assistant tells classifier WHAT was being done).
    # Max 200 chars per turn to stay within llama-3.1-8b-instant token budget.
    _history_context = ""
    if conversation_history and len(text.split()) <= 8:
        # Only inject history context for short messages (likely follow-ups)
        # Long messages are self-contained and don't need context injection.
        _recent = [
            turn for turn in (conversation_history or [])
            if turn.get("role") in ("user", "assistant")
        ][-4:]  # last 2 pairs max
        if _recent:
            _history_context = "\n".join(
                f"{'Пользователь' if t['role'] == 'user' else 'Ассистент'}: {str(t.get('content', ''))[:150]}"
                for t in _recent
            )

    pre_label = await _llm_pre_classify(text, history_context=_history_context)
    if pre_label == "weather":
        logger.info("classify: LLM pre-check → WEATHER", extra={"lang": lang})
        return _build_result(Intent.WEATHER, 0.85, lang, text)
    if pre_label == "route":
        logger.info("classify: LLM pre-check → SEARCH (route)", extra={"lang": lang})
        return _build_result(Intent.SEARCH, 0.87, lang, text)
    if pre_label == "accommodation":
        logger.info("classify: LLM pre-check → SEARCH (accommodation)", extra={"lang": lang})
        return _build_result(Intent.SEARCH, 0.85, lang, text)
    if pre_label == "emotional":
        logger.info("classify: LLM pre-check → EMOTIONAL", extra={"lang": lang})
        return _build_result(Intent.EMOTIONAL, 0.82, lang, text)
    if pre_label == "search":
        logger.info("classify: LLM pre-check → SEARCH (general)", extra={"lang": lang})
        return _build_result(Intent.SEARCH, 0.83, lang, text)
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

        # For short texts (< 6 words) we require higher confidence to avoid
        # spurious MAPS/WEATHER matches on unrecognised-language input.
        # Example: "Rigami sila maanna qanoq ippa?" (Inuktitut) was scoring
        # above 0.55 for MAPS due to accidental embedding similarity.
        #
        # analysis_hints adjustment: if analysis detected IS_SHORT or IS_MULTILINGUAL,
        # raise effective_min further — structural signal confirms low confidence is unreliable.
        # If analysis detected HAS_CODE_BLOCK or HAS_URL, lower effective_min slightly —
        # structural clarity supports the embedding result.
        word_count = len(text.split()) if analysis_hints is None else analysis_hints.word_count
        effective_min = 0.75 if word_count < 6 else _MIN_CONFIDENCE

        if analysis_hints is not None:
            if analysis_hints.has(HintType.IS_SHORT) or analysis_hints.has(HintType.IS_MULTILINGUAL):
                # Short or mixed-script input → raise bar to avoid spurious matches
                effective_min = max(effective_min, 0.72)
            if analysis_hints.has(HintType.HAS_CODE_BLOCK):
                # Structural code signal → trust embedding result more
                effective_min = min(effective_min, 0.50)

        if best_score < effective_min:
            logger.info("classify: best score below threshold", extra={
                "intent": best_intent_name,
                "score": f"{best_score:.3f}",
                "threshold": effective_min,
                "word_count": word_count,
            })
            # ── keyword fallback (last resort before QUESTION) ────────────────
            # Triggered only when LLM pre-classifier failed AND embedding score
            # is below threshold. Language-agnostic — covers top-priority intents
            # that must never silently fall to QUESTION.
            kw_lower = text.lower()
            _WEATHER_KW = {
                "погода", "weather", "температур", "forecast", "дождь", "rain",
                "снег", "snow", "ветер", "wind", "облачн", "cloudy", "sunny",
                "солнечн", "жарко", "холодно", "humid", "влажн",
                "ამინდი",  # Georgian
            }
            _SEARCH_KW = {
                "найди", "поищи", "поиск", "найти", "search", "find", "look up",
                "отель", "гостиниц", "хостел", "hotel", "hostel", "accommodation",
                "новост", "news", "аниме", "anime", "manga", "фильм", "сериал",
                "recommend", "посоветуй", "посовет",
            }
            for kw in _WEATHER_KW:
                if kw in kw_lower:
                    logger.info("classify: keyword fallback → WEATHER", extra={"kw": kw})
                    return _build_result(Intent.WEATHER, 0.75, lang, text)
            for kw in _SEARCH_KW:
                if kw in kw_lower:
                    logger.info("classify: keyword fallback → SEARCH", extra={"kw": kw})
                    return _build_result(Intent.SEARCH, 0.75, lang, text)
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
        return _build_result(intent, round(best_score, 3), lang, text)

    except Exception as exc:
        logger.error("classify failed", extra={"error": str(exc)}, exc_info=True)
        return fallback