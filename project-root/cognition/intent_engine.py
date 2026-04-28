from dataclasses import dataclass
from enum import Enum


# ─── INTENT TAXONOMY ─────────────────────────────────────────────────────────

class Intent(str, Enum):
    QUESTION        = "question"        # factual / informational query
    INSTRUCTION     = "instruction"     # do something, step-by-step
    CODE            = "code"            # write / fix / explain code
    ANALYSIS        = "analysis"        # analyse data / text / document
    CREATIVE        = "creative"        # write / generate creative content
    CONVERSATION    = "conversation"    # small talk / greeting
    MATH            = "math"            # calculation / formula
    UNKNOWN         = "unknown"


# ─── RESULT CONTRACT ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float           # 0.0 – 1.0, heuristic-based
    system_prompt: str          # ready-to-use system prompt for this intent
    requires_retrieval: bool    # hint for retrieval layer
    requires_tools: bool        # hint for agent layer


# ─── SYSTEM PROMPT TEMPLATES ─────────────────────────────────────────────────

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
    Intent.UNKNOWN: (
        "You are a helpful assistant. "
        "Do your best to understand and respond to the user's request."
    ),
}


# ─── STRUCTURAL SIGNALS ───────────────────────────────────────────────────────
# No semantic inference — pattern matching on structure only.

_CODE_SIGNALS     = ("```", "def ", "class ", "import ", "function ", "return ", "var ", "const ")
_MATH_SIGNALS     = ("=", "∑", "∫", "√", "calculate", "solve", "formula", "equation")
_QUESTION_ENDS    = ("?",)
_CREATIVE_SIGNALS = ("write a", "write me", "poem", "story", "essay", "generate", "create a")
_ANALYSIS_SIGNALS = ("analyse", "analyze", "compare", "evaluate", "review", "summarize", "summarise")
_INSTRUCTION_SIGNALS = ("how to", "how do i", "steps to", "guide", "explain how", "walk me through")
_GREETING_SIGNALS = ("hello", "hi", "hey", "good morning", "good evening", "thanks", "thank you")


def classify(text: str) -> IntentResult:
    """
    Classify user intent from structural signals in the message text.
    Deterministic. No LLM call. No external I/O.
    """
    lower = text.lower().strip()

    # ── code ─────────────────────────────────────────────
    if any(s in text for s in _CODE_SIGNALS):
        return _result(Intent.CODE, 0.9, requires_retrieval=False, requires_tools=False)

    # ── math ─────────────────────────────────────────────
    if any(s in lower for s in _MATH_SIGNALS):
        return _result(Intent.MATH, 0.8, requires_retrieval=False, requires_tools=False)

    # ── analysis ─────────────────────────────────────────
    if any(s in lower for s in _ANALYSIS_SIGNALS):
        return _result(Intent.ANALYSIS, 0.85, requires_retrieval=True, requires_tools=False)

    # ── creative ─────────────────────────────────────────
    if any(s in lower for s in _CREATIVE_SIGNALS):
        return _result(Intent.CREATIVE, 0.85, requires_retrieval=False, requires_tools=False)

    # ── instruction ──────────────────────────────────────
    if any(s in lower for s in _INSTRUCTION_SIGNALS):
        return _result(Intent.INSTRUCTION, 0.85, requires_retrieval=True, requires_tools=False)

    # ── question ─────────────────────────────────────────
    if lower.endswith(_QUESTION_ENDS):
        return _result(Intent.QUESTION, 0.8, requires_retrieval=True, requires_tools=False)

    # ── conversation ─────────────────────────────────────
    if any(s in lower for s in _GREETING_SIGNALS):
        return _result(Intent.CONVERSATION, 0.9, requires_retrieval=False, requires_tools=False)

    # ── fallback ─────────────────────────────────────────
    return _result(Intent.UNKNOWN, 0.4, requires_retrieval=True, requires_tools=False)


def _result(
    intent: Intent,
    confidence: float,
    requires_retrieval: bool,
    requires_tools: bool,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=_SYSTEM_PROMPTS[intent],
        requires_retrieval=requires_retrieval,
        requires_tools=requires_tools,
    )