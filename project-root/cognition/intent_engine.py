from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

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
    EXAM         = "exam"
    UNKNOWN      = "unknown"

# Интенты, которые требуют инструментов
_TOOL_MAP: dict[Intent, str] = {
    Intent.WEATHER:  "weather",
    Intent.SEARCH:   "search",
    Intent.MAPS:     "maps",
    Intent.MAPS_POI: "maps_poi",
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


# ─── LANGUAGE LAYER ───────────────────────────────────────────────────────────

_LANG_NAMES: dict[str, str] = {
    "ru": "Russian",        "en": "English",         "de": "German",
    "fr": "French",         "es": "Spanish",          "pt": "Portuguese",
    "it": "Italian",        "tr": "Turkish",          "ar": "Arabic",
    "zh": "Chinese",        "ja": "Japanese",         "ko": "Korean",
    "pl": "Polish",         "uk": "Ukrainian",        "fa": "Persian (Farsi)",
    "nl": "Dutch",          "sv": "Swedish",          "no": "Norwegian",
    "da": "Danish",         "fi": "Finnish",          "cs": "Czech",
    "sk": "Slovak",         "ro": "Romanian",         "hu": "Hungarian",
    "bg": "Bulgarian",      "hr": "Croatian",         "sr": "Serbian",
    "he": "Hebrew",         "vi": "Vietnamese",       "th": "Thai",
    "id": "Indonesian",     "ms": "Malay",            "hi": "Hindi",
    "bn": "Bengali",        "ur": "Urdu",             "az": "Azerbaijani",
    "kk": "Kazakh",         "uz": "Uzbek",            "ka": "Georgian",
    "hy": "Armenian",       "mn": "Mongolian",        "sw": "Swahili",
    "am": "Amharic",
}


def _lang_directive(lang: str) -> str:
    lang_name = _LANG_NAMES.get(lang)
    if lang_name:
        return (
            f"CRITICAL INSTRUCTION: The user is writing in {lang_name}. "
            f"You MUST respond EXCLUSIVELY in {lang_name}. "
            f"Do NOT use any English words, phrases, or sentences unless the user wrote in English. "
            f"Do NOT mix languages. Every single word of your response must be in {lang_name}. "
            "This instruction overrides everything else.\n\n"
        )
    return (
        "CRITICAL INSTRUCTION: Detect the language of the user's message. "
        "Respond EXCLUSIVELY in that same language. "
        "Do NOT mix languages or use English unless the user wrote in English.\n\n"
    )


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
        "If you are unsure, say so explicitly. Do not pad answers with unnecessary preamble. "
        + _NO_CUTOFF + _FORMAT_RULES
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
        "You are a precise mathematical assistant. "
        "Show your work step by step. "
        "State the final answer clearly and unambiguously."
    ),
    Intent.EXAM: (
        "You are an exam answer assistant for school exams (OGE, EGE, VPR and equivalents). "
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
        "Summarise them clearly, cite sources, and answer the user's question directly. "
        "NEVER say you cannot search or that your data is outdated — you have live results. "
        "NEVER make up information — only use what is in the context. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.MAPS: (
        "You are a location assistant with access to real-time geocoding data. "
        "The location data in your context is current and accurate. "
        "Present coordinates, addresses, and map links clearly. "
        "NEVER say you cannot show maps or provide location data — you have it in context. "
        + _NO_CUTOFF + _FORMAT_RULES
    ),
    Intent.MAPS_POI: (
        "You are a location assistant specialising in points of interest. "
        "The place data in your context is current — fetched from Google Maps right now. "
        "Present it clearly: name, address, rating, hours, contacts. "
        "NEVER say you cannot find place information — you have it in context. "
        + _NO_CUTOFF + _FORMAT_RULES
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


async def classify(
    text: str,
    lang: str = "en",
    supabase=None,
    hf_client=None,
    conversation_history: list[dict] | None = None,
) -> IntentResult:
    """
    Classify user intent via BGE embedding + Supabase pgvector similarity.

    Falls back to Intent.QUESTION if:
      - supabase or hf_client not provided
      - embedding fails
      - no match above MIN_CONFIDENCE
    """
    fallback = _build_result(Intent.QUESTION, 0.70, lang, text)

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

        if best_score < _MIN_CONFIDENCE:
            logger.info("classify: best score below MIN_CONFIDENCE", extra={
                "intent": best_intent_name,
                "score": f"{best_score:.3f}",
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
        return _build_result(intent, round(best_score, 3), lang, text)

    except Exception as exc:
        logger.error("classify failed", extra={"error": str(exc)}, exc_info=True)
        return fallback