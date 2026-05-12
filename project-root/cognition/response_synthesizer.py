from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier
from i18n.strings import t as _t, normalize_lang, _SILENT_KEYS

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_CHARS = 4096


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def get_system_message(key: str, lang: str) -> str:
    return _t(key, lang) or "⚠️ An error occurred."


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
    """
    import re

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
      5. correction   — meta/correction
      6. finalize     — truncate to Telegram limit
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
    text = _structure(text, inp.intent)
    text = _format(text)
    text = _apply_correction(text)
    text, truncated = _finalize(text, lang)

    return SynthesisResult(text=text, truncated=truncated)