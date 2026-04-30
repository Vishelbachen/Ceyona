from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    QUESTION        = "question"
    INSTRUCTION     = "instruction"
    CODE            = "code"
    ANALYSIS        = "analysis"
    CREATIVE        = "creative"
    CONVERSATION    = "conversation"
    MATH            = "math"
    WEATHER         = "weather"
    SEARCH          = "search"
    UNKNOWN         = "unknown"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float
    system_prompt: str
    requires_retrieval: bool
    requires_tools: bool
    tool_name: str = ""
    tool_params: dict = None

    def __post_init__(self):
        if self.tool_params is None:
            object.__setattr__(self, "tool_params", {})


_SYSTEM_PROMPTS: dict[Intent, str] = {
    Intent.QUESTION: (
        "You are a precise and concise assistant. "
        "Answer the user's question directly and factually. "
        "If you are unsure, say so explicitly."
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant. "
        "Provide clear, numbered step-by-step instructions. "
        "Be complete but concise."
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, well-commented code. "
        "Always specify the language. Explain your approach briefly."
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant. "
        "Structure your analysis clearly with key findings first. "
        "Be objective and evidence-based."
    ),
    Intent.CREATIVE: (
        "You are a creative writing assistant. "
        "Be imaginative, engaging, and original. "
        "Match the tone and style the user requests."
    ),
    Intent.CONVERSATION: (
        "You are a friendly and helpful assistant. "
        "Keep responses conversational and appropriately brief."
    ),
    Intent.MATH: (
        "You are a precise mathematical assistant. "
        "Show your work step by step. "
        "State the final answer clearly."
    ),
    Intent.WEATHER: (
        "You are a helpful assistant providing weather information. "
        "Present weather data clearly and concisely."
    ),
    Intent.SEARCH: (
        "You are a helpful assistant. "
        "Summarize search results clearly and concisely."
    ),
    Intent.UNKNOWN: (
        "You are a helpful assistant. "
        "Do your best to understand and respond to the user's request."
    ),
}

_CODE_SIGNALS = (
    "```", "def ", "class ", "import ", "function ", "return ",
    "var ", "const ", "let ", "print(", "console.log", "#!/",
    "напиши код", "напиши скрипт", "write code", "write a script",
    "write a function", "write a program", "fix this code",
    "исправь код", "почини код", "debug", "дебаг",
)
_MATH_SIGNALS = (
    "=", "∑", "∫", "√", "calculate", "solve", "formula",
    "equation", "вычисли", "посчитай", "реши", "сколько будет",
    "how much is", "what is", "%", "процент", "percent",
    "производная", "integral", "matrix", "матрица",
)
_QUESTION_ENDS = ("?", "؟", "？")
_CREATIVE_SIGNALS = (
    "write a", "write me", "poem", "story", "essay",
    "generate", "create a", "напиши", "сочини", "придумай",
    "стихотворение", "рассказ", "сказку", "песню",
)
_ANALYSIS_SIGNALS = (
    "analyse", "analyze", "compare", "evaluate", "review",
    "summarize", "summarise", "проанализируй", "сравни",
    "оцени", "резюмируй", "объясни почему", "explain why",
)
_INSTRUCTION_SIGNALS = (
    "how to", "how do i", "steps to", "guide", "explain how",
    "walk me through", "как", "как сделать", "как установить",
    "как настроить", "покажи как", "научи",
)
_GREETING_SIGNALS = (
    "hello", "hi", "hey", "good morning", "good evening",
    "thanks", "thank you", "привет", "здравствуй", "добрый",
    "спасибо", "пока", "bye", "salut", "hola", "naber",
    "merhaba", "ciao", "こんにちは", "안녕",
)
_WEATHER_SIGNALS = (
    "weather", "погода", "погоду", "температура", "temperature",
    "дождь", "rain", "snow", "снег", "forecast", "прогноз",
    "холодно", "жарко", "тепло", "cold", "hot", "warm",
    "sunny", "cloudy", "облачно", "ветер", "wind",
    "hava", "météo", "wetter", "clima", "meteo",
)
_SEARCH_SIGNALS = (
    "найди", "поищи", "search for", "find", "look up",
    "what happened", "latest", "news", "новости", "что произошло",
    "кто такой", "who is", "что такое", "what is",
    "tell me about", "расскажи о", "информация о",
)


def _extract_city(text: str) -> str:
    """Simple city extraction from weather query."""
    lower = text.lower()
    markers = [
        "в ", "in ", "at ", "for ", "weather in ", "погода в ",
        "погоду в ", "weather at ", "температура в ",
    ]
    for marker in markers:
        idx = lower.find(marker)
        if idx != -1:
            rest = text[idx + len(marker):].strip()
            city = rest.split()[0].rstrip("?.!,")
            if city:
                return city
    # fallback: last word
    words = text.strip().rstrip("?.!").split()
    return words[-1] if words else ""


def classify(text: str) -> IntentResult:
    lower = text.lower().strip()

    # ── weather ──────────────────────────────────────────
    if any(s in lower for s in _WEATHER_SIGNALS):
        city = _extract_city(text)
        return _result(
            Intent.WEATHER, 0.9,
            requires_retrieval=False,
            requires_tools=True,
            tool_name="weather",
            tool_params={"city": city} if city else {},
        )

    # ── code ─────────────────────────────────────────────
    if any(s in text for s in _CODE_SIGNALS):
        return _result(Intent.CODE, 0.9,
                       requires_retrieval=False, requires_tools=False)

    # ── math ─────────────────────────────────────────────
    if any(s in lower for s in _MATH_SIGNALS):
        return _result(Intent.MATH, 0.8,
                       requires_retrieval=False, requires_tools=False)

    # ── analysis ─────────────────────────────────────────
    if any(s in lower for s in _ANALYSIS_SIGNALS):
        return _result(Intent.ANALYSIS, 0.85,
                       requires_retrieval=True, requires_tools=False)

    # ── creative ─────────────────────────────────────────
    if any(s in lower for s in _CREATIVE_SIGNALS):
        return _result(Intent.CREATIVE, 0.85,
                       requires_retrieval=False, requires_tools=False)

    # ── instruction ──────────────────────────────────────
    if any(s in lower for s in _INSTRUCTION_SIGNALS):
        return _result(Intent.INSTRUCTION, 0.85,
                       requires_retrieval=True, requires_tools=False)

    # ── search ───────────────────────────────────────────
    if any(s in lower for s in _SEARCH_SIGNALS):
        return _result(Intent.SEARCH, 0.8,
                       requires_retrieval=False, requires_tools=True,
                       tool_name="search",
                       tool_params={"query": text, "num": 5})

    # ── question ─────────────────────────────────────────
    if any(lower.endswith(e) for e in _QUESTION_ENDS):
        return _result(Intent.QUESTION, 0.8,
                       requires_retrieval=True, requires_tools=False)

    # ── conversation ─────────────────────────────────────
    if any(s in lower for s in _GREETING_SIGNALS):
        return _result(Intent.CONVERSATION, 0.9,
                       requires_retrieval=False, requires_tools=False)

    # ── fallback ─────────────────────────────────────────
    return _result(Intent.UNKNOWN, 0.4,
                   requires_retrieval=True, requires_tools=False)


def _result(
    intent: Intent,
    confidence: float,
    requires_retrieval: bool,
    requires_tools: bool,
    tool_name: str = "",
    tool_params: dict = None,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=_SYSTEM_PROMPTS[intent],
        requires_retrieval=requires_retrieval,
        requires_tools=requires_tools,
        tool_name=tool_name,
        tool_params=tool_params or {},
    )