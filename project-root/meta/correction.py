from __future__ import annotations

import re

# ─── BOILERPLATE PATTERNS TO STRIP ────────────────────────────────────────────
# These are common LLM preamble / sign-off artifacts that add no value.
# Matched case-insensitively at the start or end of the response.

_PREAMBLE_PATTERNS: list[re.Pattern] = [
    # English: "Sure! / Of course! / Certainly! / Absolutely! / Great!"
    re.compile(r"^(sure[!,.]?\s*|of course[!,.]?\s*|certainly[!,.]?\s*|absolutely[!,.]?\s*|great[!,.]?\s*)", re.IGNORECASE),
    # English: "Here is your ..." / "Here's the ..."
    re.compile(r"^(here(?:'s| is)(?: your| the)?\s+(?:answer|response|result|code|explanation|text|solution)[:\s]*\n*)", re.IGNORECASE),
    # English: "I'd be happy to help..." / "I'm happy to assist..."
    re.compile(r"^(i(?:'d| would) be (?:happy|glad|delighted) to (?:help|assist)[!.,]?\s*\n*)", re.IGNORECASE),
    # English: "As an AI language model, ..."
    re.compile(r"^(as an ai(?: language)? model[,.]?\s*)", re.IGNORECASE),
    # English sign-offs
    re.compile(r"\n*i hope (?:this|that) (?:helps|was helpful)[!.]?\s*$", re.IGNORECASE),
    re.compile(r"\n*(?:please )?let me know if you(?:'ve| have) any (?:more )?questions[!.]?\s*$", re.IGNORECASE),
    re.compile(r"\n*feel free to (?:ask|reach out)[^.!?\n]{0,60}[!.]?\s*$", re.IGNORECASE),
    re.compile(r"\n*is there anything else i(?: can| could)(?: help you with)?[?!.]?\s*$", re.IGNORECASE),

    # Russian preambles
    re.compile(r"^(конечно[!,.]?\s*|разумеется[!,.]?\s*|с удовольствием[!,.]?\s*)", re.IGNORECASE),
    re.compile(r"^(давайте\s+(?:разберём|рассмотрим|посмотрим)[^\n]{0,60}\n*)", re.IGNORECASE),
    re.compile(r"^(отвечу на ваш вопрос[.!]?\s*\n*)", re.IGNORECASE),
    re.compile(r"^(да,?\s+я\s+могу\s+помочь[.!]?\s*\n*)", re.IGNORECASE),
    re.compile(r"\n*если у вас (?:есть )?(?:ещё )?вопросы[^.!?\n]{0,40}[!.]?\s*$", re.IGNORECASE),
    re.compile(r"\n*надеюсь,? (?:это )?помогло[!.]?\s*$", re.IGNORECASE),
    # Russian meta-commentary openers (vision / context analysis artifacts)
    # These appear when the model describes what it "sees" instead of answering.
    # Strip the opener phrase only — the real answer follows after it.
    re.compile(r"^похоже,?\s+что\s+у\s+нас\s+есть\s+[^\n]{0,80}\.\s*\n+", re.IGNORECASE),
    re.compile(r"^этот\s+вопрос\s+не\s+связан\s+с[^\n]{0,120}\.\s*\n+", re.IGNORECASE),
    re.compile(r"^данный\s+вопрос\s+(?:не\s+)?[^\n]{0,80}\.\s*\n+", re.IGNORECASE),
    re.compile(r"^изображени[ея]\s+представляет\s+собой\s+", re.IGNORECASE),
    re.compile(r"^изображени[ея]\s+представляют\s+собой\s+[^\n]{0,80}\.\s*\n*", re.IGNORECASE),
    re.compile(r"^на\s+(?:данном|этом|всех|представленных)\s+изображени[яхе]\s+[^\n]{0,80}\.\s*\n*", re.IGNORECASE),

    # German preambles
    re.compile(r"^(natürlich[!,.]?\s*|selbstverständlich[!,.]?\s*|gerne[!,.]?\s*)", re.IGNORECASE),
    re.compile(r"^(ich helfe (?:dir|ihnen) gerne[!.,]?\s*\n*)", re.IGNORECASE),
    re.compile(r"\n*(?:falls|wenn) (?:du|sie) (?:noch )?fragen (?:hast|haben)[^.!?\n]{0,40}[!.]?\s*$", re.IGNORECASE),

    # French preambles
    re.compile(r"^(bien sûr[!,.]?\s*|bien sur[!,.]?\s*|certainement[!,.]?\s*|avec plaisir[!,.]?\s*)", re.IGNORECASE),
    re.compile(r"^(je vais vous aider[.!]?\s*\n*|je peux vous aider[.!]?\s*\n*)", re.IGNORECASE),
    re.compile(r"\n*n'hésitez pas à (?:me )?(?:poser|demander)[^.!?\n]{0,40}[!.]?\s*$", re.IGNORECASE),

    # Spanish preambles
    re.compile(r"^(claro[!,.]?\s*|por supuesto[!,.]?\s*|¡claro[!,.]?\s*)", re.IGNORECASE),
    re.compile(r"^(con gusto[!,.]?\s*|encantado de ayudar[.!]?\s*\n*)", re.IGNORECASE),
    re.compile(r"\n*si tienes (?:más )?preguntas[^.!?\n]{0,40}[!.]?\s*$", re.IGNORECASE),

    # Turkish preambles
    re.compile(r"^(tabii[!,.]?\s*|tabii ki[!,.]?\s*|elbette[!,.]?\s*|memnuniyetle[!,.]?\s*)", re.IGNORECASE),
    re.compile(r"\n*başka sorularınız (?:olursa|varsa)[^.!?\n]{0,40}[!.]?\s*$", re.IGNORECASE),

    # Georgian preambles
    re.compile(r"^(რა თქმა უნდა[!,.]?\s*|სიამოვნებით[!,.]?\s*)", re.IGNORECASE),

    # Arabic preambles
    re.compile(r"^(بالتأكيد[!,.]?\s*|بكل سرور[!,.]?\s*|حبًا وكرامة[!,.]?\s*)", re.IGNORECASE),

    # Universal: "Да, конечно." / "Yes, of course." variants already covered above
    # "Привет!" as opener when user didn't greet
    re.compile(r"^(привет[!,.]?\s*(?=\S))", re.IGNORECASE),
]

# ─── MARKDOWN FIXERS ──────────────────────────────────────────────────────────

_RE_TRIPLE_BACKTICK = re.compile(r"```")
_RE_BOLD_MARKER     = re.compile(r"\*\*")
_RE_ITALIC_MARKER   = re.compile(r"(?<!\*)\*(?!\*)")

# ─── WHITESPACE ───────────────────────────────────────────────────────────────

_RE_EXCESSIVE_BLANKS = re.compile(r"\n{4,}")
_RE_TRAILING_SPACE   = re.compile(r"[ \t]+$", re.MULTILINE)


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _strip_preamble(text: str) -> str:
    """Remove common LLM boilerplate from start and end."""
    for pattern in _PREAMBLE_PATTERNS:
        text = pattern.sub("", text)
    return text


def _fix_markdown(text: str) -> str:
    """
    Fix unclosed markdown markers.
    Rule: if a marker appears an odd number of times → append a closing marker.
    Only applied to triple backticks and bold (**) — safest heuristics.
    """
    # Triple backticks: odd count → unclosed code block
    backtick_count = len(_RE_TRIPLE_BACKTICK.findall(text))
    if backtick_count % 2 != 0:
        text = text.rstrip() + "\n```"

    # Bold markers: odd count → unclosed bold
    bold_count = len(_RE_BOLD_MARKER.findall(text))
    if bold_count % 2 != 0:
        text = text.rstrip() + "**"

    return text


def _normalise_whitespace(text: str) -> str:
    """Collapse 4+ consecutive blank lines to 2, strip trailing spaces per line."""
    text = _RE_TRAILING_SPACE.sub("", text)
    text = _RE_EXCESSIVE_BLANKS.sub("\n\n\n", text)
    return text.strip()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def apply(text: str) -> str:
    """
    Apply lightweight text correction.

    Called exclusively by response_synthesizer at step 4.
    Must never raise — caller (synthesizer) handles exceptions by keeping original.

    Pipeline:
      1. Strip LLM boilerplate preambles / sign-offs
      2. Fix unclosed markdown markers
      3. Normalise whitespace

    Returns corrected text. If result would be empty, returns original.
    """
    if not text or not text.strip():
        return text

    result = _strip_preamble(text)
    result = _fix_markdown(result)
    result = _normalise_whitespace(result)

    # Safety: never return empty — synthesizer will discard anyway, but be explicit
    return result if result.strip() else text