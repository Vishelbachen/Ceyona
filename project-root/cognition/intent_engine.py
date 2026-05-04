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
    MAPS         = "maps"
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

_LANG_NAMES: dict[str, str] = {
    "ru": "Russian",       "en": "English",        "de": "German",
    "fr": "French",        "es": "Spanish",         "pt": "Portuguese",
    "it": "Italian",       "tr": "Turkish",         "ar": "Arabic",
    "zh": "Chinese",       "ja": "Japanese",        "ko": "Korean",
    "pl": "Polish",        "uk": "Ukrainian",       "fa": "Persian (Farsi)",
    "nl": "Dutch",         "sv": "Swedish",         "no": "Norwegian",
    "da": "Danish",        "fi": "Finnish",         "cs": "Czech",
    "sk": "Slovak",        "ro": "Romanian",        "hu": "Hungarian",
    "bg": "Bulgarian",     "hr": "Croatian",        "sr": "Serbian",
    "he": "Hebrew",        "vi": "Vietnamese",      "th": "Thai",
    "id": "Indonesian",    "ms": "Malay",           "hi": "Hindi",
    "bn": "Bengali",       "ur": "Urdu",            "az": "Azerbaijani",
    "kk": "Kazakh",        "uz": "Uzbek",           "ka": "Georgian",
    "hy": "Armenian",      "mn": "Mongolian",       "sw": "Swahili",
    "am": "Amharic",
}


def _lang_directive(lang: str) -> str:
    lang_name = _LANG_NAMES.get(lang)
    if lang_name:
        return (
            f"IMPORTANT: The user writes in {lang_name}. "
            f"You MUST reply exclusively in {lang_name}. "
            "Never switch languages. Never reply in English unless the user wrote in English.\n\n"
        )
    return (
        "IMPORTANT: Detect the language of the user's message and reply "
        "exclusively in that same language. Never switch languages.\n\n"
    )


# ─── BASE SYSTEM PROMPTS ──────────────────────────────────────────────────────

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
    directive = _lang_directive(lang)
    base = _BASE_PROMPTS[intent]
    return directive + base


# ─── SIGNAL TABLES ────────────────────────────────────────────────────────────

_CODE_SIGNALS: tuple[str, ...] = (
    "```", "def ", "class ", "import ", "return ", "function ",
    "var ", "const ", "let ", "print(", "console.log", "#!/",
    "write code", "write a script", "write a function", "write a program",
    "fix this code", "fix the code", "fix my code", "refactor",
    "debug this", "debug the", "implement", "unit test",
    "напиши код", "напиши скрипт", "напиши функцию", "напиши программу",
    "исправь код", "почини код", "отрефактори", "реализуй",
    "дебаг", "отладь",
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
    "გამარჯობა", "მადლობა", "ნახვამდის",
    "բարև", "շնորհակալություն",
)

_WEATHER_SIGNALS: tuple[str, ...] = (
    # English
    "weather", "forecast", "temperature", "rain", "snow", "sunny",
    "cloudy", "humidity", "wind", "storm", "celsius", "fahrenheit",
    # Russian
    "погода", "прогноз погоды", "температура", "дождь", "снег",
    "облачно", "ветер", "жарко", "холодно", "тепло", "прогноз",
    # European
    "météo", "wetter", "clima", "meteo", "weer", "väder",
    "vädret", "vejr", "sää", "idő", "počasí", "vreme",
    # Turkish
    "hava durumu", "yağmur", "kar yağıyor",
    # Arabic
    "طقس", "الطقس", "حرارة", "مطر", "ثلج",
    # Chinese
    "天气", "温度", "下雨", "下雪", "天氣",
    # Japanese
    "天気", "気温", "雨", "雪", "晴れ",
    # Korean
    "날씨", "기온", "비", "눈",
    # Hindi
    "मौसम", "तापमान", "बारिश", "बर्फ",
    # Georgian
    "ამინდი", "ტემპერატურა", "წვიმა", "თოვლი", "ქარი",
    # Armenian
    "եղանակ", "ջերմաստիճան", "անձրև",
    # Azerbaijani
    "yağış", "qar", "külək",
    # Kazakh
    "ауа райы", "жаңбыр", "қар",
    # Uzbek
    "ob-havo", "yomg'ir", "qor",
    # Hebrew
    "מזג אוויר", "גשם", "שלג",
    # Vietnamese
    "thời tiết", "nhiệt độ", "mưa",
    # Thai
    "อากาศ", "ฝน", "หิมะ",
    # Indonesian / Malay
    "cuaca", "hujan", "salju", "suhu",
)

_SEARCH_SIGNALS: tuple[str, ...] = (
    "search for", "look up", "find information", "find out",
    "what happened", "latest news", "news about", "who is",
    "tell me about", "what is the current",
    "найди", "поищи", "найди информацию", "новости", "что произошло",
    "кто такой", "расскажи о", "информация о", "последние новости",
)

_QUESTION_ENDS: tuple[str, ...] = ("?", "؟", "？", "?")


# ─── CITY STOP WORDS ──────────────────────────────────────────────────────────
# Particles, temporal markers, articles — never city names

_CITY_STOP_WORDS: frozenset[str] = frozenset({
    # Georgian
    "ამ", "ახლა", "წუთას", "დღეს", "ახლახან", "რა", "არის", "სად",
    # Russian
    "сейчас", "сегодня", "прямо", "там", "здесь", "это", "какая", "какой",
    "будет", "есть", "сейчас", "данный", "этот",
    # English
    "now", "today", "currently", "right", "there", "here",
    "the", "a", "an", "is", "what", "how",
    # Turkish
    "şu", "an", "şimdi", "bugün", "orada", "nasıl", "ne",
    # Arabic
    "الآن", "اليوم", "هناك", "في", "هذا", "ما", "كيف",
    # Hindi
    "अभी", "आज", "वहाँ", "यहाँ", "क्या", "कैसा",
    # French
    "maintenant", "aujourd", "hui", "là", "ce", "cette", "quel", "quelle",
    # German
    "jetzt", "heute", "dort", "hier", "das", "die", "der", "wie", "was",
    # Spanish / Portuguese
    "ahora", "hoy", "allí", "aquí", "agora", "hoje", "lá", "qué", "cual",
    # Italian
    "adesso", "oggi", "là", "qui", "che",
    # Polish / Ukrainian
    "teraz", "dziś", "там", "тут", "зараз", "сьогодні", "яка", "який",
    # Indonesian / Malay
    "sekarang", "hari", "ini", "di", "sana", "apa", "bagaimana",
    # Japanese
    "今", "現在", "そこ", "の", "は", "が",
    # Korean
    "지금", "오늘", "거기", "의", "는", "가",
    # Chinese
    "现在", "今天", "那里", "這裡", "的", "什么", "怎么",
    # Hebrew
    "עכשיו", "היום", "שם", "מה", "איך",
    # Thai
    "ตอนนี้", "วันนี้", "ที่นั่น",
    # Vietnamese
    "bây", "giờ", "hôm", "nay", "đó", "thế", "nào",
})


# ─── CITY MARKERS ─────────────────────────────────────────────────────────────

_CITY_MARKERS: tuple[str, ...] = (
    # English
    "weather in ", "forecast for ", "temperature in ", "in ",
    # Russian
    "погода в ", "прогноз для ", "температура в ", "в ",
    # European
    "wetter in ", "météo à ", "clima en ", "weer in ",
    "väder i ", "vädret i ", "vejr i ", "sää ",
    # Turkish
    "hava durumu ", "hava ",
    # Arabic
    "طقس في ", "في ",
    # Chinese
    "天气 ", "的天气",
    # Japanese
    "の天気", "天気 ",
    # Korean
    "날씨 ", "의 날씨",
    # Hindi
    "का मौसम", "में मौसम", "में ",
    # Georgian
    "ამინდი ", "ამინდია ",
    # Armenian
    "եղանակը ",
    # Indonesian / Malay
    "cuaca di ", "di ",
)


def _extract_city(text: str) -> str:
    """
    Extract city name from weather query.

    Strategy:
      1. Georgian postposition -ში: word ending in ში, len > 4, not a stop word
      2. Marker-based: find marker, scan following words, skip stop words
      3. Fallback: last non-trivial non-stop word in text
    """
    lower = text.lower()

    # ── Georgian postposition -ში ─────────────────────────────────────────────
    if "ში" in text:
        words = text.split()
        for word in words:
            if word.endswith("ში") and len(word) > 4:
                city = word[:-2].rstrip("?.!,")
                if len(city) > 2 and city.lower() not in _CITY_STOP_WORDS:
                    return city

    # ── marker-based extraction ───────────────────────────────────────────────
    for marker in _CITY_MARKERS:
        idx = lower.find(marker)
        if idx != -1:
            rest = text[idx + len(marker):].strip()
            words = rest.split()
            for word in words:
                candidate = word.rstrip("?.!,'-")
                if len(candidate) > 1 and candidate.lower() not in _CITY_STOP_WORDS:
                    return candidate

    # ── fallback: last non-trivial non-stop word ──────────────────────────────
    words = text.strip().rstrip("?.!,").split()
    candidates = [
        w.rstrip("?.!,'-") for w in words
        if len(w) > 2 and w.lower() not in _CITY_STOP_WORDS
    ]
    return candidates[-1] if candidates else ""


# ─── CORE CLASSIFY ────────────────────────────────────────────────────────────

def classify(text: str, lang: str = "en") -> IntentResult:
    """
    Classify user intent from text.
    Pure function. No I/O. Never raises.
    Always returns a valid IntentResult with a language-aware system prompt.

    Priority order:
      weather → code → math → creative → analysis →
      instruction → search → question (ends with ?) → greeting → unknown
    """
    lower = text.lower().strip()

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

    if any(s in text for s in ("```", "    ")) or any(s in lower for s in _CODE_SIGNALS):
        return _make(
            intent=Intent.CODE,
            confidence=0.90,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

    if any(s in lower for s in _MATH_SIGNALS):
        if not any(s in lower for s in _SEARCH_SIGNALS):
            return _make(
                intent=Intent.MATH,
                confidence=0.85,
                lang=lang,
                requires_retrieval=False,
                requires_tools=False,
            )

    if any(s in lower for s in _CREATIVE_SIGNALS):
        return _make(
            intent=Intent.CREATIVE,
            confidence=0.88,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

    if any(s in lower for s in _ANALYSIS_SIGNALS):
        return _make(
            intent=Intent.ANALYSIS,
            confidence=0.85,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

    if any(s in lower for s in _INSTRUCTION_SIGNALS):
        return _make(
            intent=Intent.INSTRUCTION,
            confidence=0.85,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

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

    if any(lower.endswith(e) for e in _QUESTION_ENDS):
        return _make(
            intent=Intent.QUESTION,
            confidence=0.80,
            lang=lang,
            requires_retrieval=True,
            requires_tools=False,
        )

    if any(s in lower for s in _GREETING_SIGNALS) or len(lower.split()) <= 3:
        return _make(
            intent=Intent.CONVERSATION,
            confidence=0.88,
            lang=lang,
            requires_retrieval=False,
            requires_tools=False,
        )

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