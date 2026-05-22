from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier
from i18n.strings import _SILENT_KEYS, normalize_lang
from i18n.strings import t as _t

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_CHARS = 4096


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

# DEPRECATED: use i18n.t.get_system_message instead.
# These helpers are pure i18n wrappers — they do not belong in cognition/.
# Kept here for backward compatibility only. transport/ must NOT import from here
# (architecture.md §19: transport → cognition is forbidden).
# Canonical location: i18n/t.py
def get_system_message(key: str, lang: str) -> str:
    return _t(key, lang) or "⚠️ An error occurred."


# DEPRECATED: use i18n.t.format_balance_message instead.
def format_balance_message(balance: float, lang: str) -> str:
    return _t("balance_display", lang, amount=f"{balance:.2f}")


# ─── I/O CONTRACTS ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: "Intent | None"
    tier: Tier
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    truncated: bool = False


# ─── INTERNAL PIPELINE ────────────────────────────────────────────────────────

def _assemble(raw: str) -> str:
    return raw


def _structure(text: str, intent: "Intent | None") -> str:
    return text


def _convert_latex_to_plaintext(text: str) -> str:
    """
    Convert LaTeX math expressions to readable Unicode plaintext.
    Telegram does not render LaTeX — raw commands display as literal text.
    Called before stripping delimiters so inner content is converted first.

    Code blocks (``` and inline `) are extracted before LaTeX conversion
    and restored afterwards — underscore inside code must never be treated
    as a LaTeX subscript marker.
    """
    import re

    # ── protect code blocks from LaTeX substitution ───────────────────────
    _placeholders: list[str] = []

    def _stash(m: re.Match) -> str:
        _placeholders.append(m.group(0))
        return f"\x00CODE{len(_placeholders) - 1}\x00"

    # fenced blocks first (``` ... ```), then inline `...`
    text = re.sub(r"```[\s\S]*?```", _stash, text)
    text = re.sub(r"`[^`\n]+`", _stash, text)

    # ── superscripts / subscripts ─────────────────────────────────────────
    # Full superscript map: digits, signs, letters with Unicode coverage
    _SUP_MAP = {
        "0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵",
        "6":"⁶","7":"⁷","8":"⁸","9":"⁹","+":"⁺","-":"⁻",
        "=":"⁼","(":"⁽",")":"⁾","n":"ⁿ","i":"ⁱ",
        # uppercase: use small-caps approximations
        "A":"ᴬ","B":"ᴮ","D":"ᴰ","E":"ᴱ","G":"ᴳ","H":"ᴴ",
        "I":"ᴵ","J":"ᴶ","K":"ᴷ","L":"ᴸ","M":"ᴹ","N":"ᴺ",
        "O":"ᴼ","P":"ᴾ","R":"ᴿ","T":"ᵀ","U":"ᵁ","V":"ⱽ",
        "W":"ᵂ",
        # lowercase
        "a":"ᵃ","b":"ᵇ","c":"ᶜ","d":"ᵈ","e":"ᵉ","f":"ᶠ",
        "g":"ᵍ","h":"ʰ","j":"ʲ","k":"ᵏ","l":"ˡ","m":"ᵐ",
        "o":"ᵒ","p":"ᵖ","r":"ʳ","s":"ˢ","t":"ᵗ","u":"ᵘ",
        "v":"ᵛ","w":"ʷ","x":"ˣ","y":"ʸ","z":"ᶻ",
    }
    def _sup_char(c: str) -> str:
        return _SUP_MAP.get(c, c)
    _SUB = str.maketrans("0123456789+-=()aeinoruvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑᵢₙₒᵣᵤᵥₓ")

    def sup(m: re.Match) -> str:
        inner = m.group(1).strip("{}")
        return "".join(_sup_char(c) for c in inner)

    def sub(m: re.Match) -> str:
        inner = m.group(1).strip("{}")
        return inner.translate(_SUB)

    # ^{...} or ^x  — superscript
    text = re.sub(r"\^\{([^}]*)\}", sup, text)
    text = re.sub(r"\^([A-Za-z0-9])", lambda m: _sup_char(m.group(1)), text)

    # _{...} or _x  — subscript
    text = re.sub(r"_\{([^}]*)\}", sub, text)
    text = re.sub(r"_([A-Za-z0-9])", lambda m: m.group(1).translate(_SUB), text)

    # ── fractions: \frac{a}{b} → a/b ─────────────────────────────────────
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", text)

    # ── Greek letters → Unicode ───────────────────────────────────────────
    _GREEK = {
        "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
        "epsilon": "ε", "theta": "θ", "lambda": "λ", "mu": "μ",
        "pi": "π", "sigma": "σ", "tau": "τ", "phi": "φ", "omega": "ω",
        "Alpha": "Α", "Beta": "Β", "Gamma": "Γ", "Delta": "Δ",
        "Theta": "Θ", "Lambda": "Λ", "Sigma": "Σ", "Omega": "Ω",
    }
    for name, sym in _GREEK.items():
        text = text.replace(f"\\{name}", sym)

    # ── common math symbols ───────────────────────────────────────────────
    _SYMBOLS = [
        (r"\\times", "×"), (r"\\cdot", "·"), (r"\\div", "÷"),
        (r"\\pm", "±"),    (r"\\mp", "∓"),   (r"\\neq", "≠"),
        (r"\\leq", "≤"),   (r"\\geq", "≥"),  (r"\\approx", "≈"),
        (r"\\infty", "∞"), (r"\\sqrt", "√"), (r"\\sum", "Σ"),
        (r"\\prod", "Π"),  (r"\\int", "∫"),  (r"\\partial", "∂"),
        (r"\\in", "∈"),    (r"\\notin", "∉"), (r"\\subset", "⊂"),
        (r"\\cup", "∪"),   (r"\\cap", "∩"),  (r"\\to", "→"),
        (r"\\Rightarrow", "⇒"), (r"\\Leftrightarrow", "⟺"),
        (r"\\ldots", "…"), (r"\\cdots", "⋯"),
    ]
    for pattern, sym in _SYMBOLS:
        text = re.sub(pattern, sym, text)

    # ── strip remaining \command braces: \text{abc} → abc ─────────────────
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)

    # ── strip lone braces left over ───────────────────────────────────────
    text = re.sub(r"(?<!\\)[{}]", "", text)

    # ── restore protected code blocks ─────────────────────────────────────
    for i, block in enumerate(_placeholders):
        text = text.replace(f"\x00CODE{i}\x00", block)

    return text


def _normalize_for_telegram(text: str) -> str:
    """Strip LaTeX, Markdown tables, headers, bold/italic — anything Telegram cannot render."""
    import re

    # Convert LaTeX math content to Unicode BEFORE stripping delimiters
    text = _convert_latex_to_plaintext(text)

    # LaTeX math delimiters (now just wrappers — content already converted)
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"\1", text)

    # Markdown headers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Bold and italic
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_(.*?)_", r"\1", text)

    # Markdown table separator rows: |---|---| or |:--|:--:|
    text = re.sub(r"^[ \t]*\|[ \t]*[-:]+[ \t]*(\|[ \t]*[-:]+[ \t]*)+\|?[ \t]*$", "", text, flags=re.MULTILINE)

    # Markdown table data rows: | cell | cell | → "cell  cell"
    def flatten_row(m: re.Match) -> str:
        inner = m.group(0)
        cells = [c.strip() for c in inner.split("|") if c.strip()]
        return "  ".join(cells)

    text = re.sub(r"^[ \t]*\|.+\|[ \t]*$", flatten_row, text, flags=re.MULTILINE)

    # Any remaining lone | characters used as table-like formatting
    # Only strip lines that are mostly pipes (formatting artifacts)
    def strip_pipe_lines(m: re.Match) -> str:
        line = m.group(0)
        pipe_count = line.count("|")
        non_pipe = len(line.replace("|", "").strip())
        # If pipes dominate (formatting line), strip pipes
        if pipe_count > 0 and non_pipe < pipe_count * 4:
            return line.replace("|", "  ").strip()
        return line
    text = re.sub(r"^.+\|.+$", strip_pipe_lines, text, flags=re.MULTILINE)

    # Collapse 3+ blank lines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.splitlines())

    return text.strip()


def _format(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _apply_correction(text: str) -> str:
    try:
        from meta.correction import apply
        corrected = apply(text)
        return corrected if corrected and corrected.strip() else text
    except Exception:
        return text


def _apply_normalizer(text: str, lang: str) -> str:
    """
    Step 6: output_normalizer — strip retrieval contamination artifacts.
    Removes:  source attribution tags, garbled URLs, English leak terms.
    Never changes meaning. Safe to call unconditionally.
    """
    try:
        from meta.output_normalizer import apply as _norm
        result = _norm(text, lang)
        return result if result and result.strip() else text
    except Exception:
        return text


def _strip_cot_artifacts(text: str, intent: "Intent | None") -> str:
    """
    Step 2.5 (audit §13.3): Strip chain-of-thought reasoning artifacts from final response.

    Two-mode strategy:
    A) Pure CoT loop detection — if 2+ loop signals found, the whole response IS the
       debug output (no real answer exists). Replace with honest admission.
       Handles the 'infinite candidate search' pattern seen in screenshots.
    B) Partial header stripping — remove CoT section headers while keeping real content.

    Rule: MATH/EXAM intent → pass through (CoT IS the answer for these).
    """
    import re

    from cognition.intent_engine import Intent as _Intent

    # MATH and EXAM CoT is intentional — never strip it
    if intent in (_Intent.MATH, _Intent.EXAM):
        return text

    # ── Mode A: Pure CoT loop detection ──────────────────────────────────────
    # If 2+ loop signals present → entire response is a constraint-matching loop
    # with no real answer. Replace with honest admission instead of showing debug.
    _LOOP_SIGNALS = [
        re.compile(r"Ограничения:\s*\n\s*\d+\.", re.IGNORECASE),
        re.compile(r"Кандидаты:\s*\n\s*\d+\.", re.IGNORECASE),
        re.compile(r"После(?:\s+долгого)?\s+поиска\s+я\s+нашёл", re.IGNORECASE),
        re.compile(r"Однако\s+я\s+нашёл\s+ещё\s+одного", re.IGNORECASE),
        re.compile(r"Чтобы\s+исправить\s+нарушенные\s+ограничения", re.IGNORECASE),
        re.compile(r"Constraints?:\s*\n\s*\d+\.", re.IGNORECASE),
        re.compile(r"Candidates?:\s*\n\s*\d+\.", re.IGNORECASE),
        re.compile(r"After\s+(?:a\s+)?(?:long\s+)?search\s+I\s+found", re.IGNORECASE),
        re.compile(r"However,?\s+I\s+found\s+another", re.IGNORECASE),
    ]
    loop_signal_count = sum(1 for p in _LOOP_SIGNALS if p.search(text))

    if loop_signal_count >= 2:
        # Detect language by Cyrillic presence
        _has_cyrillic = re.search(r"[а-яёА-ЯЁ]", text)
        if _has_cyrillic:
            return "Не могу точно определить — попробуй дать подсказку или уточнить вопрос."
        return "I'm not sure — could you give me a hint or more context?"

    # ── Mode B: Partial CoT header stripping ─────────────────────────────────
    # Remove known scaffolding headers while preserving real answer content.
    _COT_HEADER_PATTERNS = [
        # English scaffolding headers
        re.compile(r"^Constraints?:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Candidates?:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Verification(?: table)?:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Step-by-step(?: reasoning)?:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Chain of thought:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Reasoning:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Analysis:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Think(ing| step):\s*\n", re.MULTILINE | re.IGNORECASE),
        # English multi-line scaffold blocks (header + numbered/dash body)
        re.compile(
            r"^(?:Constraints?|Candidates?|Verification|Analysis|Reasoning):\s*\n"
            r"(?:[ \t]*[-\d\.].+\n)+",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Russian scaffolding headers
        re.compile(r"^Ограничения:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Кандидаты:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Верификация(?: таблица)?:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Проверка:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Рассуждение:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Анализ:\s*\n", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^Шаг за шагом:\s*\n", re.MULTILINE | re.IGNORECASE),
        # Russian multi-line scaffold blocks
        re.compile(
            r"^(?:Ограничения|Кандидаты|Верификация|Проверка|Рассуждение|Анализ):\s*\n"
            r"(?:[ \t]*[-\d\.].+\n)+",
            re.MULTILINE | re.IGNORECASE,
        ),
    ]

    result = text
    for _ in range(3):
        prev = result
        for pattern in _COT_HEADER_PATTERNS:
            result = pattern.sub("", result)
        if result == prev:
            break

    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result if result.strip() else text

def _truncate(text: str, lang: str) -> tuple[str, bool]:
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    suffix = _t("truncation_suffix", lang)
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


def _finalize(text: str, lang: str) -> tuple[str, bool]:
    return _truncate(text, lang)


# ─── MAIN SYNTHESIZER ─────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into the final user-facing message.

    Pipeline:
      1. assemble     — accept raw text
      2. structure    — intent-aware shaping
      3. normalize    — strip LaTeX/Markdown Telegram can't render
      4. format       — whitespace normalisation
      5. correction   — meta/correction (preamble/sign-off stripping)
      6. normalizer   — meta/output_normalizer (retrieval contamination cleanup)
      7. finalize     — truncate to Telegram limit
    """
    lang = normalize_lang(inp.lang)

    # ── DENY path ─────────────────────────────────────────────────────────────
    if inp.denied:
        # Use deny_reason as key if it's a known silent key, else look up message
        if inp.deny_reason in _SILENT_KEYS:
            return SynthesisResult(text="")
        # Try deny_reason as a string key; fall back to default_deny
        msg = _t(inp.deny_reason, lang)
        if not msg:
            msg = _t("default_deny", lang)
        return SynthesisResult(text=msg)

    # ── no LLM response ───────────────────────────────────────────────────────
    if not inp.raw_text or not inp.raw_text.strip():
        from cognition.intent_engine import Intent as _Intent
        if inp.intent == _Intent.EMOTIONAL:
            return SynthesisResult(text=_t("emotional_fallback", lang))
        return SynthesisResult(text=_t("no_response", lang))

    # ── normal pipeline ───────────────────────────────────────────────────────
    text = _assemble(inp.raw_text)
    text = _normalize_for_telegram(text)
    text = _strip_cot_artifacts(text, inp.intent)   # §13.3: remove CoT scaffolding for non-MATH
    text = _structure(text, inp.intent)
    text = _format(text)
    text = _apply_correction(text)
    text = _apply_normalizer(text, lang)
    text, truncated = _finalize(text, lang)

    return SynthesisResult(text=text, truncated=truncated)