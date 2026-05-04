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
    Intent.MAPS: (
        "You are a helpful location assistant. "
        "Provide coordinates, addresses, and location information clearly. "
        "Be concise and precise."
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
    "where is",                 # "where is the Eiffel Tower"
    "where are",                # "where are the pyramids"
    "location of",              # "location of Big Ben"
    "address of",               # "address of the Kremlin"
    "coordinates of",           # "coordinates of Mount Everest"
    "how to get to",            # "how to get to the airport"
    "directions to",            # "directions to Central Park"
    "navigate to",              # "navigate to Times Square"
    "find on map",
    "show on map",
    "show me on map",
    "map of",                   # "map of Berlin"
    "locate",                   # "locate the nearest hospital"
    "get directions",
    "route to",
    "nearest ",                 # "nearest pharmacy"
    "closest ",                 # "closest subway station"

    # ── Russian ───────────────────────────────────────────────────────────────
    "где находится",            # "где находится вокзал"
    "где находятся",
    "где расположен",
    "где расположена",
    "адрес магазина",           # anchored: адрес + object
    "адрес кафе",
    "адрес ресторана",
    "адрес аптеки",
    "адрес больницы",
    "адрес офиса",
    "адрес отеля",
    "адрес гостиницы",
    "покажи адрес",
    "координаты места",         # anchored: координаты + места/города/etc.
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
    "местоположение",           # standalone — specific enough
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
    "ближайший ",               # "ближайший банкомат"
    "ближайшая ",               # "ближайшая аптека"
    "маршрут до",
    "маршрут к",
    "дорога до",
    "путь до",
    "навигация до",
    "построй маршрут",

    # ── Georgian ──────────────────────────────────────────────────────────────
    "სად არის",
    "მდებარეობა",
    "კოორდინატები",             # Georgian — no rhetorical use pattern
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
    "nächste ",                 # "nächste Apotheke"

    # ── French ────────────────────────────────────────────────────────────────
    "où est",
    "où se trouve",
    "adresse de",
    "coordonnées de",
    "comment aller",
    "itinéraire vers",
    "sur la carte",
    "le plus proche",           # "le plus proche hôpital"

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
    "coordenadas de",
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
    "nerede",                   # standalone — unambiguous in Turkish
    "nereye",
    "konumu nedir",
    "adresi nedir",
    "koordinatları",            # anchored by Turkish plural/possessive suffix
    "haritada göster",
    "yol tarifi",
    "en yakın ",

    # ── Arabic ────────────────────────────────────────────────────────────────
    "أين يقع",
    "أين توجد",
    "موقع ",                    # "موقع المطار" — anchored by following noun
    "عنوان ",
    "إحداثيات ",
    "على الخريطة",
    "كيف أصل",
    "اتجاهات إلى",

    # ── Chinese ───────────────────────────────────────────────────────────────
    "在哪里",
    "在哪儿",
    "的位置",                   # "X的位置" — anchored
    "的地址",                   # "X的地址"
    "的坐标",                   # "X的坐标"
    "怎么去",
    "地图上",
    "最近的",

    # ── Japanese ──────────────────────────────────────────────────────────────
    "どこにある",
    "どこですか",
    "の場所",                   # "Xの場所"
    "の住所",                   # "Xの住所"
    "の座標",                   # "Xの座標"
    "行き方",
    "地図で",
    "一番近い",

    # ── Korean ────────────────────────────────────────────────────────────────
    "어디에 있",                # "어디에 있어요?"
    "의 위치",                  # "X의 위치"
    "의 주소",                  # "X의 주소"
    "의 좌표",                  # "X의 좌표"
    "가는 방법",
    "지도에서",
    "가장 가까운",

    # ── Hindi ─────────────────────────────────────────────────────────────────
    "कहाँ है",
    "कहाँ स्थित",
    "का स्थान",                 # "X का स्थान"
    "का पता",                   # "X का पता"
    "के निर्देशांक",            # "X के निर्देशांक"
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
    "hvor er",
    "hvor ligger",
    "adressen på",
    "koordinater for",
    "hvordan kommer jeg",
    "på kortet",
    "nærmeste ",

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
    "adresa ",
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
# even when a maps signal matched. These catch rhetorical questions, complaints,
# and meta-questions about the bot that happen to contain maps vocabulary.

_MAPS_NEGATIVE_GUARDS: tuple[str, ...] = (
    # Russian rhetorical / complaint patterns
    "не можешь",        # "координаты дать не можешь?"
    "не можете",
    "не умеешь",
    "не умеете",
    "в смысле",         # "в смысле? координаты дать не можешь?"