from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ─── INTENT TAXONOMY ──────────────────────────────────────────────────────────

class Intent(str, Enum):
    QUESTION     = "question"
    CODE         = "code"
    ANALYSIS     = "analysis"
    CREATIVE     = "creative"
    CONVERSATION = "conversation"
    MATH         = "math"
    INSTRUCTION  = "instruction"
    WEATHER      = "weather"
    SEARCH       = "search"
    UNKNOWN      = "unknown"


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float
    system_prompt: str
    requires_retrieval: bool
    requires_tools: bool
    tool_name: str = ""
    tool_params: dict = field(default_factory=dict)


# ─── LANGUAGE INSTRUCTION ─────────────────────────────────────────────────────
#
# This is the core of multilingual support.
# The LLM receives the user's detected language code and is instructed
# to respond in that exact language — regardless of the system prompt language.
#
# We keep system prompts in English (LLMs understand them best),
# but prepend a hard language directive that the model must follow.

_LANG_NAMES: dict[str, str] = {
    "ru": "Russian",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "tr": "Turkish",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "pl": "Polish",
    "uk": "Ukrainian",
    "fa": "Persian (Farsi)",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "cs": "Czech",
    "sk": "Slovak",
    "ro": "Romanian",
    "hu": "Hungarian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "he": "Hebrew",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "az": "Azerbaijani",
    "kk": "Kazakh",
    "uz": "Uzbek",
}


def _lang_directive(lang: str) -> str:
    """
    Build a hard language instruction prepended to every system prompt.
    The LLM must reply in the user's detected language.
    Falls back to 'the same language the user wrote in' if lang unknown.
    """
    lang_name = _LANG_NAMES.get(lang)
    if lang_name:
        return (
            f"IMPORTANT: The user writes in {lang_name}. "
            f"You MUST reply exclusively in {lang_name}. "
            "Never switch languages. Never reply in English unless the user wrote in English.\n\n"
        )
    # Unknown language code — instruct model to mirror the input language
    return (
        "IMPORTANT: Detect the language of the user's message and reply "
        "exclusively in that same language. Never switch languages.\n\n"
    )


# ─── BASE SYSTEM PROMPTS (English — model-facing) ─────────────────────────────

_BASE_PROMPTS: dict[Intent, str] = {
    Intent.QUESTION: (
        "You are a knowledgeable and direct assistant. "
        "Answer the user's question accurately and concisely. "
        "If you are unsure, say so explicitly. "
        "Do not pad the answer with unnecessary preamble."
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant specialising in step-by-step guidance. "
        "Provide clear, numbered instructions. "
        "Be complete but concise. Start directly with step 1."
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, correct, well-commented code. "
        "Always specify the programming language. "
        "Briefly explain your approach before the code block."
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant. "
        "Structure your analysis with key findings first. "
        "Be objective, evidence-based, and avoid filler."
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
    Intent.MATH: (
        "You are a precise mathematical assistant. "
        "Show your work step by step. "
        "State the final answer clearly and unambiguously."
    ),
    Intent.WEATHER: (
        "You are a helpful assistant providing weather information. "
        "Present weather data in a clear, readable format. "
        "Include temperature, conditions, and any relevant advice."
    ),
    Intent.SEARCH: (
        "You are a helpful research assistant. "
        "Summarise search results clearly and concisely. "
        "Cite sources where possible."
    ),
    Intent.UNKNOWN: (
        "You are a helpful, versatile assistant. "
        "Carefully read the user's message and respond as helpfully as possible. "
        "If the request is ambiguous, make a reasonable interpretation and answer it. "
        "Never refuse to respond just because the topic is unclear — always try."
    ),
}


def build_system_prompt(intent: Intent, lang: str) -> str:
    """
    Combine language directive + base prompt.
    This is the only function that constructs system prompts.
    """
    directive = _lang_directive(lang)
    base = _BASE_PROMPTS[intent]
    return directive + base


# ─── SIGNAL TABLES ────────────────────────────────────────────────────────────
# Ordered by specificity. Each tuple is (signal_string, case_sensitive).
# All signals are lowercase-matched unless noted.

_CODE_SIGNALS: tuple[str, ...] = (
    # universal symbols
    "```", "def ", "class ", "import ", "return ", "function ",
    "var ", "const ", "let ", "print(", "console.log", "#!/",
    # English
    "write code", "write a script", "write a function", "write a program",
    "fix this code", "fix the code", "fix my code", "refactor",
    "debug this", "debug the", "implement", "unit test",
    # Russian
    "напиши код", "напиши скрипт", "напиши функцию", "напиши программу",
    "исправь код", "почини код", "отрефактори", "реализуй",
    "дебаг", "отладь",
    # German / French / Spanish
    "schreib code", "code écrire", "escribe código",
)

_MATH_SIGNALS: tuple[str, ...] = (
    "∑", "∫", "√", "²", "³", "π",
    "calculate", "solve", "formula", "equation", "derivative",
    "integral", "matrix", "determinant", "eigenvalue",
    "вычисли", "посчитай", "реши", "сколько будет",
    "производная", "матрица", "определитель",
    "rechne", "berechne", "calculer", "calcule", "calcula",
)

_ANALYSIS_SIGNALS: tuple[str, ...] = (
    "analyse", "analyze", "compare", "evaluate", "review",
    "summarize", "summarise", "assess", "examine", "breakdown",
    "pros and cons", "advantages", "disadvantages",
    "проанализируй", "сравни", "оцени", "резюмируй",
    "объясни почему", "разбери", "плюсы и минусы",
    "analysiere", "analyser", "analysez", "analiza",
)

_CREATIVE_SIGNALS: tuple[str, ...] = (
    "write a poem", "write me a poem", "write a story", "write me a story",
    "write an essay", "write a letter", "write a song",
    "poem", "poetry", "haiku", "limerick", "sonnet",
    "create a story", "generate a story", "make up a story",
    "напиши стихотворение", "напиши стих", "напиши рассказ",
    "напиши сказку", "напиши песню", "напиши эссе", "напиши историю",
    "сочини", "придумай историю", "придумай стихотворение",
    "schreib ein gedicht", "écris un poème", "escribe un poema",
)

_INSTRUCTION_SIGNALS: tuple[str, ...] = (
    "how to", "how do i", "how do you", "steps to", "guide to",
    "explain how", "walk me through", "show me how", "tutorial",
    "как сделать", "как установить", "как настроить", "как использовать",
    "как ", "покажи как", "научи меня", "объясни как",
    "wie man", "comment faire", "cómo hacer",
)

_GREETING_SIGNALS: tuple[str, ...] = (
    "hello", "hi there", "hey there", "hey!", "hi!", "good morning",
    "good evening", "good afternoon", "good night",
    "thanks", "thank you", "thx", "ty", "bye", "goodbye", "see you",
    "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер",
    "доброе утро", "спасибо", "пока", "до свидания", "salut", "bonjour",
    "hola", "gracias", "ciao", "danke", "merci", "naber", "merhaba",
    "こんにちは", "안녕", "你好", "سلام", "مرحبا",
)

_WEATHER_SIGNALS: tuple[str, ...] = (
    "weather", "forecast", "temperature", "rain", "snow", "sunny",
    "cloudy", "humidity", "wind", "storm", "celsius", "fahrenheit",
    "погода", "прогноз погоды", "температура", "дождь", "снег",
    "облачно", "ветер", "жарко", "холодно", "тепло",
    "hava", "météo", "wetter", "clima", "meteo", "vremya",
)

_SEARCH_SIGNALS: tuple[str, ...] = (
    "search for", "look up", "find information", "find out",
    "what happened", "latest news", "news about", "who is",
    "tell me about", "what is the current",
    "найди", "поищи", "найди информацию", "новости", "что произошло",
    "кто такой", "расскажи о", "информация о", "последние новости",
)

_QUESTION_ENDS: tuple[str, ...] = ("?", "؟", "？", "?")


# ─── CITY EXTRACTOR (for weather) ────────────────────────────────────────────

_CITY_MARKERS: tuple[str, ...] = (
    "weather in ", "forecast for ", "temperature in ", "in ",
    "погода в ", "прогноз для ", "температура в ", "в ",
    "wetter in ", "météo à ", "clima en ",
)


def _extract_city(text: str) -> str:
    lower = text.lower()
    for marker in _CITY_MARKERS:
        idx = lower.find(marker)
        if idx != -1:
            rest = text[idx + len(marker):].strip()
            words = rest.split()
            if words:
                city = words[0].rstrip("?.!,")
                if len(city) > 1:
                    return city
    # fallback: last non-trivial word
    words = text.strip().rstrip("?.!,").split()
    candidates = [w for w in words if len(w) > 2]
    return candidates[-1] if candidates else ""


# ─── CORE CLASSIFY ────────────────────────────────────────────────────────────

def classify(text: str, lang: str = "en") -> IntentResult:
    """
    Classify user intent from text.
    Pure function. No I/O. Never raises.
    Always returns a valid IntentResult with a language-aware system prompt.

    Priority order (highest specificity first):
      weather → code → math → creative → analysis →
      instruction → search → question (ends with ?) → greeting → unknown
    """
    lower = text.lower().strip()

    # ── weather ──────────────────────────────────────────────────────────────
    if any(s in lower for s in _WEATHER_SIGNALS):
        city = _extract_city(text)
        return _make(
            intent=Intent.WEATHER,
            confidence=0.90,
            lang=lang,
            requires_retrieval=False,
            requires_tools=True,
            tool_name="weather",
            tool_params={"city": city, "lang": lang} if city else {"lang": lang},
        )

    # ── code (check original text for backticks / indentation) ───────────────
    if any(s in text for s in ("```", "    ")) or any(s in lower for s in _CODE_SIGNALS):
        return _make(
            intent=Intent.CODE,
            confidence=0.90,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── math ─────────────────────────────────────────────────────────────────
    if any(s in lower for s in _MATH_SIGNALS):
        # avoid false-positives from "what is" in search context
        if not any(s in lower for s in _SEARCH_SIGNALS):
            return _make(
                intent=Intent.MATH,
                confidence=0.85,
                lang=lang,
                requires_retrieval=False,
                requires_tools=False,
            )

    # ── creative ─────────────────────────────────────────────────────────────
    if any(s in lower for s in _CREATIVE_SIGNALS):
        return _make(
            intent=Intent.CREATIVE,
            confidence=0.88,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── analysis ─────────────────────────────────────────────────────────────
    if any(s in lower for s in _ANALYSIS_SIGNALS):
        return _make(
            intent=Intent.ANALYSIS,
            confidence=0.85,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

    # ── instruction ──────────────────────────────────────────────────────────
    if any(s in lower for s in _INSTRUCTION_SIGNALS):
        return _make(
            intent=Intent.INSTRUCTION,
            confidence=0.85,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

    # ── search ───────────────────────────────────────────────────────────────
    if any(s in lower for s in _SEARCH_SIGNALS):
        return _make(
            intent=Intent.SEARCH,
            confidence=0.80,
            lang=lang,
            requires_retrieval=False,
            requires_tools=True,
            tool_name="search",
            tool_params={"query": text, "num": 5, "lang": lang},
        )

    # ── question (ends with ?) ────────────────────────────────────────────────
    if any(lower.endswith(e) for e in _QUESTION_ENDS):
        return _make(
            intent=Intent.QUESTION,
            confidence=0.80,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

    # ── greeting / short social ───────────────────────────────────────────────
    if any(s in lower for s in _GREETING_SIGNALS) or len(lower.split()) <= 3:
        return _make(
            intent=Intent.CONVERSATION,
            confidence=0.88,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── unknown — always attempt to answer, never silently fail ──────────────
    return _make(
        intent=Intent.UNKNOWN,
        confidence=0.50,
        lang=lang,
        requires_retrieval=True,
        requires_tools=False,
    )


# ─── INTERNAL FACTORY ─────────────────────────────────────────────────────────

def _make(
    intent: Intent,
    confidence: float,
    lang: str,
    requires_retrieval: bool,
    requires_tools: bool,
    tool_name: str = "",
    tool_params: dict | None = None,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=build_system_prompt(intent, lang),
        requires_retrieval=requires_retrieval,
        requires_tools=requires_tools,
        tool_name=tool_name,
        tool_params=tool_params or {},
    )
