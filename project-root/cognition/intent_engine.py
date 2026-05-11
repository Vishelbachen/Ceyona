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
    EMOTIONAL    = "emotional"
    MATH         = "math"
    INSTRUCTION  = "instruction"
    WEATHER      = "weather"
    SEARCH       = "search"
    MAPS         = "maps"
    MAPS_POI     = "maps_poi"   # points of interest: hours, ratings, contacts
    EXAM         = "exam"       # school exams: ОГЭ, ЕГЭ, ВПР
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


# ─── BASE SYSTEM PROMPTS ──────────────────────────────────────────────────────

# ─── NO-CUTOFF MANDATE ───────────────────────────────────────────────────────
# Injected into every system prompt to absolutely forbid outdated-data disclaimers.
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
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant specialising in step-by-step guidance. "
        "Provide clear, numbered instructions. "
        "Be complete but concise. Start directly with step 1. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, correct, well-commented code. "
        "Always specify the programming language. "
        "Briefly explain your approach before the code block. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant with access to real-time web data provided in context. "
        "Structure your analysis with key findings first. "
        "Base your analysis on the provided context where available. "
        "Be objective, evidence-based, and avoid filler. "
        + _NO_CUTOFF
        + _FORMAT_RULES
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
        "Keep your response SHORT (1–3 sentences). "
        "Respond in the same language the user wrote in, using natural informal speech for that language. "
        "After acknowledging, you may gently ask what happened or offer to help — but only one soft question, never a list."
    ),
    Intent.MATH: (
        "You are a precise mathematical assistant. "
        "Show your work step by step. "
        "State the final answer clearly and unambiguously."
    ),
    Intent.EXAM: (
        "You are an exam answer assistant for Russian school exams (ОГЭ, ЕГЭ, ВПР). "
        "STRICT RULES — follow exactly: "
        "1. Always choose the MOST TYPICAL textbook answer — use standard school definitions only. "
        "2. Never add edge cases, nuance, or conditions not present in the question. "
        "3. Never use 'если', 'может быть', 'иногда', 'в зависимости от', 'как правило'. "
        "4. Give the final answer FIRST on the first line, then 1–2 lines of explanation maximum. "
        "5. For matching tasks: output only the answer sequence (e.g. '2 1 1 2 1'), then brief reasoning per item. "
        "6. For true/false tasks: state which statements are correct, then one-line justification each. "
        "7. Base reasoning on the most common school biology/chemistry/physics/geography textbook interpretation. "
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
        "The data IS current. " + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.SEARCH: (
        "You are a research assistant with access to live web search results. "
        "The search results in your context were fetched from the web RIGHT NOW. "
        "Summarise them clearly, cite sources, and answer the user's question directly. "
        "NEVER say you cannot search or that your data is outdated — you have live results. "
        "NEVER make up information — only use what is in the context. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.MAPS: (
        "You are a location assistant with access to real-time geocoding data. "
        "The location data in your context is current and accurate. "
        "Present coordinates, addresses, and map links clearly. "
        "NEVER say you cannot show maps or provide location data — you have it in context. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.MAPS_POI: (
        "You are a location assistant specialising in points of interest. "
        "The place data in your context is current — fetched from Google Maps right now. "
        "Present it clearly: name, address, rating, hours, contacts. "
        "NEVER say you cannot find place information — you have it in context. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
    Intent.UNKNOWN: (
        "You are a helpful, versatile assistant. "
        "You have access to real-time web search results in your context. "
        "Use the context to answer accurately. "
        "If the request is ambiguous, make a reasonable interpretation and answer it. "
        "Never refuse to respond — always try. "
        + _NO_CUTOFF
        + _FORMAT_RULES
    ),
}


def build_system_prompt(intent: Intent, lang: str) -> str:
    directive = _lang_directive(lang)
    base = _BASE_PROMPTS.get(intent, _BASE_PROMPTS[Intent.UNKNOWN])
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

# ─── EMOTIONAL SIGNALS ────────────────────────────────────────────────────────
# Short emotional reactions — frustration, disbelief, surprise, despair.
# Colloquial and profane vocabulary is intentionally included: these are
# emotional signals, not unsafe content.
_EMOTIONAL_SIGNALS: tuple[str, ...] = (
    # Russian — frustration / disbelief / despair
    "пиздец", "пиздос", "ппц", "пц", "блять", "блин", "бляха", "бля",
    "ёлки", "ёпта", "ёп", "ебать", "ебать-колотить", "капец", "капэц",
    "капец", "жопа", "жесть", "ужас", "кошмар", "всё пропало", "всё",
    "не может быть", "серьёзно?", "да ладно", "да ну", "да ты что",
    "офигеть", "офигел", "охренеть", "охренел", "фигасе", "фигня",
    "вот это да", "ничего себе", "ну и ну", "ну нихрена", "нихрена",
    "блин блинский", "звиздец", "пздц", "пздец", "писец",
    # English — frustration / disbelief / surprise
    "wtf", "omg", "omfg", "ffs", "oh no", "no way", "seriously?",
    "you're kidding", "you gotta be kidding", "unbelievable", "oh god",
    "oh shit", "holy shit", "holy crap", "damn", "dammit", "dang",
    "what the hell", "what the heck", "are you serious", "oh man",
    "oh wow", "wow", "geez", "jeez", "shoot", "crap", "awful", "terrible",
    "this is insane", "that's insane", "that is insane", "insane",
    "i can't believe", "brutal", "tragic", "devastating",
    # German
    "scheiße", "schei?e", "mist", "verdammt", "krass", "heftig", "alter",
    "echt jetzt", "boah", "was zur hölle", "nicht zu fassen",
    # French
    "merde", "putain", "mon dieu", "c'est pas vrai", "incroyable",
    "n'importe quoi", "oh là là", "c'est nul",
    # Spanish
    "joder", "hostia", "dios mío", "qué asco", "increíble",
    "no puede ser", "qué horror", "es una mierda",
    # Turkish
    "lanet olsun", "kahretsin", "allah kahretsin", "inanılmaz", "berbat",
    "rezalet", "ya ne", "eyvah",
    # Arabic
    "يا إلهي", "مصيبة", "لا يصدق", "يا ربي", "كارثة", "هذا جنون",
    # Hebrew
    "אלוהים", "לא יאומן", "איזה בלגן", "נורא",
    # Chinese
    "我的天", "天哪", "不会吧", "太惨了", "完了", "太糟了",
    # Japanese
    "やばい", "まじか", "信じられない", "最悪", "ひどい",
    # Korean
    "헐", "대박", "말도 안 돼", "진짜요", "세상에",
    # Georgian
    "ღმერთო ჩემო", "რა საშინელებაა", "ვაი", "ვაიმე",
    # Armenian
    "աստված իմ", "անհավատալի", "ահա թե ինչ", "վայ",
    # Azerbaijani
    "ay allah", "dəhşət", "inanılmaz", "vay",
    # Kazakh / Uzbek
    "жаман", "мынау не", "ой, жаман", "voy",
    # Ukrainian
    "боже мій", "жах", "жесть", "да ладно", "не може бути",
    "капець", "капцям", "оце так", "ото ж бо",
    # Polish
    "kurwa", "o boże", "niesamowite", "co za horror", "tragedia",
    # Hindi
    "अरे यार", "क्या बात है", "यार ये क्या है", "बुरा हुआ",
    # Indonesian / Malay
    "ya ampun", "gila", "tidak mungkin", "astaga", "sial",
    # Thai
    "โอ้โห", "ไม่น่าเชื่อ", "แย่จัง", "โห",
    # Vietnamese
    "trời ơi", "không thể tin được", "thật tệ",
    # Portuguese
    "meu deus", "que horror", "inacreditável", "que merda", "caramba",
    # Italian
    "dio mio", "che schifo", "incredibile", "mannaggia", "accidenti",
)

# Maximum character length for a message to be treated as a pure emotional reaction.
# Longer messages with emotional words are handled as QUESTION/CONVERSATION instead.
_EMOTIONAL_MAX_LEN = 60


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

# ─── EXAM SIGNALS ─────────────────────────────────────────────────────────────
#
# Triggers strict exam mode for ОГЭ/ЕГЭ/ВПР questions.
# Must fire BEFORE all other classifiers.

_EXAM_SIGNALS: tuple[str, ...] = (
    "огэ", "егэ", "впр", "гиа",
    "задание 1", "задание 2", "задание 3", "задание 4", "задание 5",
    "задание 6", "задание 7", "задание 8", "задание 9", "задание 10",
    "задание 11", "задание 12", "задание 13", "задание 14", "задание 15",
    "задание 16", "задание 17", "задание 18", "задание 19", "задание 20",
    "задание 21", "задание 22", "задание 23", "задание 24", "задание 25",
    "установите соответствие",
    "сопоставьте",
    "верны ли суждения",
    "верно ли суждение",
    "суждение а", "суждение б", "суждение в",
    "признак а", "признак б", "признак в", "признак г", "признак д",
    "выберите верные суждения",
    "выберите верные ответы",
    "какие из перечисленных",
    "какие из следующих",
    "к каждому элементу",
    "цифру, которая",
    "цифры, которые",
    "запишите в таблицу",
    "вставьте пропущенное слово",
    "вставьте пропущенные слова",
    "расположите в правильном порядке",
    "правильная последовательность",
)

# ─── MAPS POI SIGNALS ─────────────────────────────────────────────────────────
#
# RULE: signals must anchor to POI-specific attributes — hours, ratings,
# phone numbers, reviews, website. Generic location queries go to MAPS.
# MAPS_POI fires when the user asks ABOUT a place, not WHERE a place is.

_MAPS_POI_SIGNALS: tuple[str, ...] = (
    # ── English ───────────────────────────────────────────────────────────────
    "opening hours",            # "opening hours of the museum"
    "opening times",
    "what time does",           # "what time does the pharmacy open"
    "what time do",
    "is it open",               # "is it open now"
    "is open now",
    "closes at",
    "opens at",
    "hours of operation",
    "business hours",
    "phone number of",          # "phone number of the clinic"
    "contact number",
    "phone number",
    "rating of",                # "rating of this restaurant"
    "reviews of",
    "review of",
    "how good is",
    "is it worth",
    "website of",               # "website of the hotel"
    "official website",
    "menu of",                  # "menu of the cafe"
    "price of",                 # "price of entry"
    "admission fee",
    "entry fee",
    "ticket price",
    "how much does it cost to enter",
    "how much to get in",

    # ── Russian ───────────────────────────────────────────────────────────────
    "часы работы",              # "часы работы музея"
    "режим работы",
    "когда открывается",
    "когда закрывается",
    "во сколько открывается",
    "во сколько закрывается",
    "сейчас открыто",
    "сейчас работает",
    "работает сейчас",
    "открыто сейчас",
    "телефон ",                 # "телефон аптеки"
    "номер телефона",
    "контакты ",
    "как позвонить",
    "рейтинг ",                 # "рейтинг ресторана"
    "отзывы о",
    "отзывы на",
    "стоит ли идти",
    "стоит посетить",
    "сайт ",                    # "сайт отеля"
    "официальный сайт",
    "меню ",                    # "меню кафе"
    "цена входа",
    "стоимость билета",
    "сколько стоит вход",
    "сколько стоит посещение",
    "стоимость посещения",

    # ── German ────────────────────────────────────────────────────────────────
    "öffnungszeiten",
    "wann öffnet",
    "wann schließt",
    "ist geöffnet",
    "telefonnummer",
    "bewertung von",
    "rezensionen",
    "webseite von",
    "eintrittspreise",

    # ── French ────────────────────────────────────────────────────────────────
    "heures d'ouverture",
    "horaires",
    "est ouvert",
    "numéro de téléphone",
    "avis sur",
    "site web de",
    "prix d'entrée",
    "tarifs",

    # ── Spanish ───────────────────────────────────────────────────────────────
    "horario de",
    "a qué hora abre",
    "a qué hora cierra",
    "está abierto",
    "número de teléfono",
    "reseñas de",
    "sitio web de",
    "precio de entrada",

    # ── Portuguese ────────────────────────────────────────────────────────────
    "horário de funcionamento",
    "que horas abre",
    "que horas fecha",
    "está aberto",
    "número de telefone",
    "avaliações de",
    "site de",
    "preço de entrada",

    # ── Italian ───────────────────────────────────────────────────────────────
    "orari di apertura",
    "a che ora apre",
    "a che ora chiude",
    "è aperto",
    "numero di telefono",
    "recensioni di",
    "sito web di",
    "prezzo di ingresso",

    # ── Turkish ───────────────────────────────────────────────────────────────
    "çalışma saatleri",
    "kaçta açılıyor",
    "kaçta kapanıyor",
    "açık mı",
    "telefon numarası",
    "yorumlar",
    "web sitesi",
    "giriş ücreti",

    # ── Arabic ────────────────────────────────────────────────────────────────
    "ساعات العمل",
    "متى يفتح",
    "متى يغلق",
    "هل مفتوح",
    "رقم الهاتف",
    "تقييم ",
    "مراجعات",
    "الموقع الرسمي",
    "سعر الدخول",

    # ── Chinese ───────────────────────────────────────────────────────────────
    "营业时间",
    "几点开门",
    "几点关门",
    "现在开放吗",
    "电话号码",
    "评分",
    "评价",
    "官方网站",
    "入场费",

    # ── Japanese ──────────────────────────────────────────────────────────────
    "営業時間",
    "何時に開く",
    "何時に閉まる",
    "今開いている",
    "電話番号",
    "評価",
    "口コミ",
    "公式サイト",
    "入場料",

    # ── Korean ────────────────────────────────────────────────────────────────
    "영업시간",
    "몇 시에 열어",
    "몇 시에 닫아",
    "지금 열려있나",
    "전화번호",
    "평점",
    "리뷰",
    "공식 웹사이트",
    "입장료",

    # ── Georgian ──────────────────────────────────────────────────────────────
    "სამუშაო საათები",
    "როდის იხსნება",
    "ახლა ღიაა",
    "ტელეფონის ნომერი",
    "შეფასება",
    "ვებსაიტი",
    "შესასვლელის ფასი",

    # ── Armenian ──────────────────────────────────────────────────────────────
    "աշխատանքային ժամեր",
    "երբ է բացվում",
    "հեռախոսահամար",
    "գնահատական",
    "կայք",

    # ── Ukrainian ─────────────────────────────────────────────────────────────
    "години роботи",
    "коли відкривається",
    "коли закривається",
    "зараз відкрито",
    "номер телефону",
    "відгуки про",
    "офіційний сайт",
    "ціна входу",

    # ── Polish ────────────────────────────────────────────────────────────────
    "godziny otwarcia",
    "o której otwierają",
    "czy jest otwarte",
    "numer telefonu",
    "opinie o",
    "strona internetowa",
    "cena wejścia",

    # ── Hindi ─────────────────────────────────────────────────────────────────
    "खुलने का समय",
    "कब खुलता है",
    "अभी खुला है",
    "फोन नंबर",
    "रेटिंग",
    "समीक्षा",
    "आधिकारिक वेबसाइट",
    "प्रवेश शुल्क",
)

# ─── MAPS POI NEGATIVE GUARDS ─────────────────────────────────────────────────
#
# Suppresses MAPS_POI when signals fire in rhetorical or unrelated context.

_MAPS_POI_NEGATIVE_GUARDS: tuple[str, ...] = (
    "не можешь",
    "не можете",
    "не умеешь",
    "в смысле",
    "can't you",
    "cannot you",
    "do you even",
    "why don't you",
)

# ─── MAPS SIGNALS ─────────────────────────────────────────────────────────────
#
# RULE: every signal must be a phrase, not an isolated noun.
# Bare nouns like "координаты", "адрес", "address" are BANNED here —
# they fire on rhetorical questions ("координаты дать не можешь?")
# and unrelated sentences ("address the issue").
#
# Each entry must anchor the noun to a geographic verb or preposition
# so the classifier requires INTENT + OBJECT, not just the object alone.

_MAPS_SIGNALS: tuple[str, ...] = (
    # ── English ───────────────────────────────────────────────────────────────
    "where is",
    "where are",
    "location of",
    "address of",
    "coordinates of",
    "how to get to",
    "directions to",
    "navigate to",
    "find on map",
    "show on map",
    "show me on map",
    "map of",
    "locate",
    "get directions",
    "route to",
    "nearest ",
    "closest ",

    # ── Russian ───────────────────────────────────────────────────────────────
    "где находится",
    "где находятся",
    "где расположен",
    "где расположена",
    "адрес магазина",
    "адрес кафе",
    "адрес ресторана",
    "адрес аптеки",
    "адрес больницы",
    "адрес офиса",
    "адрес отеля",
    "адрес гостиницы",
    "покажи адрес",
    "координаты места",
    "координаты города",
    "координаты страны",
    "координаты острова",
    "координаты горы",
    "как добраться",
    "как доехать",
    "как дойти",
    "как проехать",
    "как пройти до",
    "покажи на карте",
    "найди на карте",
    "местоположение",
    "покажи местоположение",
    "расположение на карте",
    "где это находится",
    "где это",
    "где магазин",
    "где аптека",
    "где больница",
    "где метро",
    "где вокзал",
    "где аэропорт",
    "где отель",
    "ближайший ",
    "ближайшая ",
    "маршрут до",
    "маршрут к",
    "дорога до",
    "путь до",
    "навигация до",
    "построй маршрут",

    # ── Georgian ──────────────────────────────────────────────────────────────
    "სად არის",
    "მდებარეობა",
    "კოორდინატები",
    "რუკაზე",
    "მარშრუტი",
    "როგორ მივიდე",

    # ── German ────────────────────────────────────────────────────────────────
    "wo ist",
    "wo befindet sich",
    "wo liegt",
    "adresse von",
    "koordinaten von",
    "wie komme ich",
    "weg nach",
    "route nach",
    "auf der karte",
    "nächste ",

    # ── French ────────────────────────────────────────────────────────────────
    "où est",
    "où se trouve",
    "adresse de",
    "coordonnées de",
    "comment aller",
    "itinéraire vers",
    "sur la carte",
    "le plus proche",

    # ── Spanish ───────────────────────────────────────────────────────────────
    "dónde está",
    "dónde queda",
    "dónde se encuentra",
    "dirección de",
    "coordenadas de",
    "cómo llegar",
    "ruta hacia",
    "en el mapa",
    "más cercano",

    # ── Portuguese ────────────────────────────────────────────────────────────
    "onde fica",
    "onde está",
    "endereço de",
    "como chegar",
    "rota para",
    "no mapa",
    "mais próximo",

    # ── Italian ───────────────────────────────────────────────────────────────
    "dove si trova",
    "dove è",
    "indirizzo di",
    "coordinate di",
    "come arrivare",
    "percorso per",
    "sulla mappa",
    "più vicino",

    # ── Turkish ───────────────────────────────────────────────────────────────
    "nerede",
    "nereye",
    "konumu nedir",
    "adresi nedir",
    "koordinatları",
    "haritada göster",
    "yol tarifi",
    "en yakın ",

    # ── Arabic ────────────────────────────────────────────────────────────────
    "أين يقع",
    "أين توجد",
    "موقع ",
    "عنوان ",
    "إحداثيات ",
    "على الخريطة",
    "كيف أصل",
    "اتجاهات إلى",

    # ── Chinese ───────────────────────────────────────────────────────────────
    "在哪里",
    "在哪儿",
    "的位置",
    "的地址",
    "的坐标",
    "怎么去",
    "地图上",
    "最近的",

    # ── Japanese ──────────────────────────────────────────────────────────────
    "どこにある",
    "どこですか",
    "の場所",
    "の住所",
    "の座標",
    "行き方",
    "地図で",
    "一番近い",

    # ── Korean ────────────────────────────────────────────────────────────────
    "어디에 있",
    "의 위치",
    "의 주소",
    "의 좌표",
    "가는 방법",
    "지도에서",
    "가장 가까운",

    # ── Hindi ─────────────────────────────────────────────────────────────────
    "कहाँ है",
    "कहाँ स्थित",
    "का स्थान",
    "का पता",
    "के निर्देशांक",
    "कैसे पहुंचें",
    "नक्शे पर",
    "सबसे नजदीक",

    # ── Ukrainian ─────────────────────────────────────────────────────────────
    "де знаходиться",
    "де розташований",
    "де розташована",
    "адреса ",
    "координати ",
    "як дістатися",
    "як проїхати",
    "на карті",
    "найближчий ",
    "найближча ",

    # ── Polish ────────────────────────────────────────────────────────────────
    "gdzie jest",
    "gdzie znajduje się",
    "adres ",
    "współrzędne ",
    "jak dojechać",
    "jak dojść",
    "na mapie",
    "najbliższy ",

    # ── Dutch ─────────────────────────────────────────────────────────────────
    "waar is",
    "waar bevindt",
    "adres van",
    "coördinaten van",
    "hoe kom ik",
    "route naar",
    "op de kaart",
    "dichtstbijzijnde",

    # ── Swedish ───────────────────────────────────────────────────────────────
    "var är",
    "var ligger",
    "adress till",
    "koordinater för",
    "hur tar jag mig",
    "på kartan",
    "närmaste ",

    # ── Norwegian ─────────────────────────────────────────────────────────────
    "hvor er",
    "hvor ligger",
    "adresse til",
    "koordinater for",
    "hvordan kommer jeg",
    "på kartet",
    "nærmeste ",

    # ── Danish ────────────────────────────────────────────────────────────────
    "adressen på",
    "på kortet",

    # ── Finnish ───────────────────────────────────────────────────────────────
    "missä on",
    "missä sijaitsee",
    "osoite ",
    "koordinaatit ",
    "miten pääsen",
    "kartalla",
    "lähin ",

    # ── Czech / Slovak ────────────────────────────────────────────────────────
    "kde je",
    "kde se nachází",
    "adresa ",
    "souřadnice ",
    "jak se dostat",
    "na mapě",
    "nejbližší ",

    # ── Romanian ──────────────────────────────────────────────────────────────
    "unde este",
    "unde se află",
    "coordonate ",
    "cum ajung",
    "pe hartă",
    "cel mai apropiat",

    # ── Hungarian ─────────────────────────────────────────────────────────────
    "hol van",
    "hol található",
    "cím ",
    "koordináták ",
    "hogyan jutok",
    "a térképen",
    "legközelebbi ",

    # ── Hebrew ────────────────────────────────────────────────────────────────
    "איפה נמצא",
    "כתובת של",
    "קואורדינטות של",
    "איך מגיעים",
    "על המפה",
    "הקרוב ביותר",

    # ── Vietnamese ────────────────────────────────────────────────────────────
    "ở đâu",
    "địa chỉ của",
    "tọa độ của",
    "làm thế nào để đến",
    "trên bản đồ",
    "gần nhất",

    # ── Thai ──────────────────────────────────────────────────────────────────
    "อยู่ที่ไหน",
    "ที่อยู่ของ",
    "พิกัดของ",
    "วิธีไป",
    "บนแผนที่",
    "ที่ใกล้ที่สุด",

    # ── Indonesian / Malay ────────────────────────────────────────────────────
    "di mana",
    "alamat dari",
    "koordinat dari",
    "cara ke",
    "di peta",
    "terdekat",

    # ── Azerbaijani ───────────────────────────────────────────────────────────
    "harada yerləşir",
    "ünvanı nədir",
    "xəritədə göstər",
    "necə getmək",
    "ən yaxın ",

    # ── Kazakh ────────────────────────────────────────────────────────────────
    "қайда орналасқан",
    "мекенжайы",
    "картада",
    "қалай жетуге",
    "жақын жердегі",

    # ── Uzbek ─────────────────────────────────────────────────────────────────
    "qayerda joylashgan",
    "manzili",
    "xaritada",
    "qanday borish",
    "eng yaqin ",

    # ── Armenian ──────────────────────────────────────────────────────────────
    "որտեղ է",
    "հասցեն",
    "կոորդինատները",
    "ինչպես հասնել",
    "քարտեզի վրա",

    # ── Mongolian ─────────────────────────────────────────────────────────────
    "хаана байдаг",
    "хаяг нь",
    "координат нь",
    "хэрхэн очих",
    "газрын зурагт",
)

# ─── MAPS NEGATIVE GUARDS ─────────────────────────────────────────────────────
#
# If ANY of these phrases appear in the text, the MAPS classifier is suppressed
# even when a maps signal matched.

_MAPS_NEGATIVE_GUARDS: tuple[str, ...] = (
    # Russian rhetorical / complaint patterns
    "не можешь",
    "не можете",
    "не умеешь",
    "не умеете",
    "в смысле",
    # English rhetorical patterns
    "can't you",
    "cannot you",
    "do you even",
    "why don't you",
    "address the issue",
    "address the problem",
    "address this",
    "address that",
    "address your",
    # Generic "address" as verb (not location)
    "address concerns",
    "address questions",
)


# ─── CLASSIFY ─────────────────────────────────────────────────────────────────

def classify(
    text: str,
    lang: str = "en",
    conversation_history: list[dict] | None = None,
) -> IntentResult:
    """
    Classify user intent from text.

    Priority order:
      1. EXAM       (ОГЭ/ЕГЭ/ВПР — must fire before everything else)
      2. MAPS_POI  (hours, ratings, contacts — fires before MAPS)
      3. MAPS      (location, directions)
      4. WEATHER
      5. SEARCH
      6. CODE
      7. MATH
      8. ANALYSIS
      9. CREATIVE
      10. INSTRUCTION
      11. EMOTIONAL  (short emotional reactions — before CONVERSATION)
      12. CONVERSATION (greetings)
      13. QUESTION (default)
    """
    lower = text.lower()

    # ── EXAM (check first — school exam questions must never bleed into other intents) ──
    if any(signal in lower for signal in _EXAM_SIGNALS):
        return IntentResult(
            intent=Intent.EXAM,
            confidence=0.95,
            system_prompt=build_system_prompt(Intent.EXAM, lang),
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── MAPS_POI (check before MAPS — more specific) ──────────────────────────
    poi_negative = any(guard in lower for guard in _MAPS_POI_NEGATIVE_GUARDS)
    if not poi_negative:
        if any(signal in lower for signal in _MAPS_POI_SIGNALS):
            return IntentResult(
                intent=Intent.MAPS_POI,
                confidence=0.90,
                system_prompt=build_system_prompt(Intent.MAPS_POI, lang),
                requires_retrieval=False,
                requires_tools=True,
                tool_name="maps_poi",
                tool_params={"query": text, "lang": lang},
            )

    # ── MAPS ──────────────────────────────────────────────────────────────────
    maps_negative = any(guard in lower for guard in _MAPS_NEGATIVE_GUARDS)
    if not maps_negative:
        if any(signal in lower for signal in _MAPS_SIGNALS):
            return IntentResult(
                intent=Intent.MAPS,
                confidence=0.90,
                system_prompt=build_system_prompt(Intent.MAPS, lang),
                requires_retrieval=False,
                requires_tools=True,
                tool_name="maps",
                tool_params={"query": text, "lang": lang},
            )

    # ── WEATHER ───────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _WEATHER_SIGNALS):
        return IntentResult(
            intent=Intent.WEATHER,
            confidence=0.90,
            system_prompt=build_system_prompt(Intent.WEATHER, lang),
            requires_retrieval=False,
            requires_tools=True,
            tool_name="weather",
            tool_params={"query": text, "lang": lang},
        )

    # ── SEARCH ────────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _SEARCH_SIGNALS):
        return IntentResult(
            intent=Intent.SEARCH,
            confidence=0.85,
            system_prompt=build_system_prompt(Intent.SEARCH, lang),
            requires_retrieval=False,
            requires_tools=True,
            tool_name="search",
            tool_params={"query": text, "lang": lang},
        )

    # ── CODE ──────────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _CODE_SIGNALS):
        return IntentResult(
            intent=Intent.CODE,
            confidence=0.90,
            system_prompt=build_system_prompt(Intent.CODE, lang),
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── MATH ──────────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _MATH_SIGNALS):
        return IntentResult(
            intent=Intent.MATH,
            confidence=0.88,
            system_prompt=build_system_prompt(Intent.MATH, lang),
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── ANALYSIS ──────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _ANALYSIS_SIGNALS):
        return IntentResult(
            intent=Intent.ANALYSIS,
            confidence=0.85,
            system_prompt=build_system_prompt(Intent.ANALYSIS, lang),
            requires_retrieval=True,
            requires_tools=False,
        )

    # ── CREATIVE ──────────────────────────────────────────────────────────────
    if any(signal in lower for signal in _CREATIVE_SIGNALS):
        return IntentResult(
            intent=Intent.CREATIVE,
            confidence=0.88,
            system_prompt=build_system_prompt(Intent.CREATIVE, lang),
            requires_retrieval=False,
            requires_tools=False,
        )

    # ── INSTRUCTION ───────────────────────────────────────────────────────────
    if any(signal in lower for signal in _INSTRUCTION_SIGNALS):
        return IntentResult(
            intent=Intent.INSTRUCTION,
            confidence=0.85,
            system_prompt=build_system_prompt(Intent.INSTRUCTION, lang),
            requires_retrieval=True,
            requires_tools=False,
        )

    # ── EMOTIONAL (short reactions — frustration, surprise, despair) ──────────
    # Fires only on short messages so long emotional rants still reach QUESTION.
    if len(text.strip()) <= _EMOTIONAL_MAX_LEN:
        if any(signal in lower for signal in _EMOTIONAL_SIGNALS):
            return IntentResult(
                intent=Intent.EMOTIONAL,
                confidence=0.93,
                system_prompt=build_system_prompt(Intent.EMOTIONAL, lang),
                requires_retrieval=False,
                requires_tools=False,
            )

    # ── CONVERSATION (greetings / small talk) ─────────────────────────────────
    