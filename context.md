# shared_types.py





# meta/

# reflection.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ─── QUALITY SIGNALS ──────────────────────────────────────────────────────────

class QualitySignal(str, Enum):
    # Response completeness
    RESPONSE_EMPTY        = "response_empty"
    RESPONSE_TRUNCATED    = "response_truncated"
    RESPONSE_OK           = "response_ok"

    # Agent / execution path
    FALLBACK_USED         = "fallback_used"
    CONSENSUS_USED        = "consensus_used"
    TOOL_USED             = "tool_used"
    TOOL_FAILED           = "tool_failed"
    AGENT_FAILED          = "agent_failed"

    # Intent signals
    INTENT_UNKNOWN        = "intent_unknown"
    INTENT_LOW_CONFIDENCE = "intent_low_confidence"   # confidence < 0.6

    # Cost / tier signals
    TIER_UPGRADED         = "tier_upgraded"
    DEGRADED_MODE         = "degraded_mode"

    # Safety
    SAFETY_BLOCKED        = "safety_blocked"


# ─── REPORT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReflectionReport:
    """
    Semantic quality report for a completed request.

    Fields:
      user_id        — for memory_audit correlation (optional)
      session_id     — trace/span correlation
      timestamp_utc  — when the report was produced
      intent         — classified intent string
      lang           — user language code
      tier           — execution tier used
      model          — model that produced the final response
      response_len   — character length of the final response
      cost_usd       — actual cost of the request
      signals        — quality signals observed
      notes          — human-readable observations (lightweight: empty list)
      lightweight    — True when produced in DEGRADED_MODE
    """
    timestamp_utc: str
    intent: str
    lang: str
    tier: str
    model: str
    response_len: int
    cost_usd: float
    signals: list[QualitySignal]
    notes: list[str] = field(default_factory=list)
    user_id: int | None = None
    session_id: str = ""
    lightweight: bool = False

    def has_signal(self, signal: QualitySignal) -> bool:
        return signal in self.signals

    def to_dict(self) -> dict:
        return {
            "timestamp_utc": self.timestamp_utc,
            "intent":        self.intent,
            "lang":          self.lang,
            "tier":          self.tier,
            "model":         self.model,
            "response_len":  self.response_len,
            "cost_usd":      self.cost_usd,
            "signals":       [s.value for s in self.signals],
            "notes":         self.notes,
            "user_id":       self.user_id,
            "session_id":    self.session_id,
            "lightweight":   self.lightweight,
        }


# ─── INPUT CONTRACT ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReflectionInput:
    """
    Everything reflection.py needs to build a ReflectionReport.
    Populated by whoever calls reflect() — typically the orchestrator's
    post-execution cleanup path or an async side-channel task.
    """
    intent: str
    lang: str
    tier: str
    model: str
    response_text: str
    response_truncated: bool
    cost_usd: float
    agent_fallback_used: bool = False
    consensus_used: bool = False
    tool_used: bool = False
    tool_failed: bool = False
    agent_failed: bool = False
    intent_confidence: float = 1.0
    tier_was_upgraded: bool = False
    was_degraded_mode: bool = False
    safety_blocked: bool = False
    user_id: int | None = None
    session_id: str = ""


# ─── INTERNAL BUILDERS ────────────────────────────────────────────────────────

def _collect_signals(inp: ReflectionInput) -> list[QualitySignal]:
    signals: list[QualitySignal] = []

    # Response state
    if not inp.response_text or not inp.response_text.strip():
        signals.append(QualitySignal.RESPONSE_EMPTY)
    elif inp.response_truncated:
        signals.append(QualitySignal.RESPONSE_TRUNCATED)
    else:
        signals.append(QualitySignal.RESPONSE_OK)

    # Execution path
    if inp.agent_fallback_used:
        signals.append(QualitySignal.FALLBACK_USED)
    if inp.consensus_used:
        signals.append(QualitySignal.CONSENSUS_USED)
    if inp.tool_used:
        signals.append(QualitySignal.TOOL_USED)
    if inp.tool_failed:
        signals.append(QualitySignal.TOOL_FAILED)
    if inp.agent_failed:
        signals.append(QualitySignal.AGENT_FAILED)

    # Intent
    if inp.intent == "unknown":
        signals.append(QualitySignal.INTENT_UNKNOWN)
    elif inp.intent_confidence < 0.6:
        signals.append(QualitySignal.INTENT_LOW_CONFIDENCE)

    # Tier / mode
    if inp.tier_was_upgraded:
        signals.append(QualitySignal.TIER_UPGRADED)
    if inp.was_degraded_mode:
        signals.append(QualitySignal.DEGRADED_MODE)

    # Safety
    if inp.safety_blocked:
        signals.append(QualitySignal.SAFETY_BLOCKED)

    return signals


def _collect_notes(inp: ReflectionInput, signals: list[QualitySignal]) -> list[str]:
    """Human-readable observations. Only produced in full mode."""
    notes: list[str] = []

    if QualitySignal.RESPONSE_EMPTY in signals:
        notes.append("Response was empty — agent or tool produced no output.")

    if QualitySignal.FALLBACK_USED in signals:
        notes.append(f"Primary agent failed; fallback was used. Model: {inp.model}.")

    if QualitySignal.INTENT_UNKNOWN in signals:
        notes.append("Intent could not be classified — UNKNOWN fallback used.")
    elif QualitySignal.INTENT_LOW_CONFIDENCE in signals:
        notes.append(
            f"Low intent confidence ({inp.intent_confidence:.2f}) "
            f"for intent '{inp.intent}'."
        )

    if QualitySignal.TOOL_FAILED in signals:
        notes.append("External tool was called but failed. LLM path was used instead.")

    if QualitySignal.RESPONSE_TRUNCATED in signals:
        notes.append(
            f"Response truncated to Telegram limit. "
            f"Original length: {len(inp.response_text)} chars."
        )

    if QualitySignal.TIER_UPGRADED in signals:
        notes.append(f"Tier was upgraded due to intent '{inp.intent}' requirements.")

    if QualitySignal.DEGRADED_MODE in signals:
        notes.append("System ran in DEGRADED_MODE — reduced capability.")

    if QualitySignal.SAFETY_BLOCKED in signals:
        notes.append("Request was blocked by safety agent.")

    return notes


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def reflect(inp: ReflectionInput, lightweight: bool = False) -> ReflectionReport:
    """
    Build a post-execution reflection report.

    Args:
        inp:         All relevant execution data for this request.
        lightweight: True in DEGRADED_MODE — skips note generation.

    Returns:
        ReflectionReport — pure data, no side effects.
        Callers are responsible for sending it to observability / memory_audit.

    Never raises. Returns a minimal report on error.
    """
    try:
        signals = _collect_signals(inp)
        notes   = [] if lightweight else _collect_notes(inp, signals)

        return ReflectionReport(
            timestamp_utc  = _utc_now(),
            intent         = inp.intent,
            lang           = inp.lang,
            tier           = inp.tier,
            model          = inp.model,
            response_len   = len(inp.response_text),
            cost_usd       = inp.cost_usd,
            signals        = signals,
            notes          = notes,
            user_id        = inp.user_id,
            session_id     = inp.session_id,
            lightweight    = lightweight,
        )

    except Exception:
        # Meta layer must never crash the side-channel
        return ReflectionReport(
            timestamp_utc = _utc_now(),
            intent        = getattr(inp, "intent", "unknown"),
            lang          = getattr(inp, "lang", "en"),
            tier          = getattr(inp, "tier", "FAST"),
            model         = getattr(inp, "model", ""),
            response_len  = 0,
            cost_usd      = 0.0,
            signals       = [QualitySignal.RESPONSE_EMPTY],
            notes         = ["ReflectionReport construction failed."],
            lightweight   = lightweight,
        )



# correction.py

from __future__ import annotations

import re


# ─── BOILERPLATE PATTERNS TO STRIP ────────────────────────────────────────────
# These are common LLM preamble / sign-off artifacts that add no value.
# Matched case-insensitively at the start or end of the response.

_PREAMBLE_PATTERNS: list[re.Pattern] = [
    # "Sure! Here is..." / "Of course! ..."
    re.compile(r"^(sure[!,.]?\s*|of course[!,.]?\s*|certainly[!,.]?\s*|absolutely[!,.]?\s*|great[!,.]?\s*)", re.IGNORECASE),
    # "Here is your ..." / "Here's the ..."
    re.compile(r"^(here(?:'s| is)(?: your| the)?\s+(?:answer|response|result|code|explanation|text|solution)[:\s]*\n*)", re.IGNORECASE),
    # "I'd be happy to help..." / "I'm happy to assist..."
    re.compile(r"^(i(?:'d| would) be (?:happy|glad|delighted) to (?:help|assist)[!.,]?\s*\n*)", re.IGNORECASE),
    # "As an AI language model, ..."
    re.compile(r"^(as an ai(?: language)? model[,.]?\s*)", re.IGNORECASE),
    # "I hope this helps!" at the end
    re.compile(r"\n*i hope (?:this|that) (?:helps|was helpful)[!.]?\s*$", re.IGNORECASE),
    # "Let me know if you have any questions!"
    re.compile(r"\n*(?:please )?let me know if you(?:'ve| have) any (?:more )?questions[!.]?\s*$", re.IGNORECASE),
    # "Feel free to ask if you need anything else!"
    re.compile(r"\n*feel free to (?:ask|reach out)[^.!?\n]{0,60}[!.]?\s*$", re.IGNORECASE),
    # "Is there anything else I can help you with?"
    re.compile(r"\n*is there anything else i(?: can| could)(?: help you with)?[?!.]?\s*$", re.IGNORECASE),
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



# analysis.py

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


# ─── HINT TYPES ───────────────────────────────────────────────────────────────

class HintType(str, Enum):
    # Structural signals
    HAS_CODE_BLOCK   = "has_code_block"
    HAS_JSON         = "has_json"
    HAS_MATH         = "has_math"
    HAS_LIST         = "has_list"
    HAS_URL          = "has_url"

    # Length / density signals
    IS_SHORT         = "is_short"         # ≤ 20 words
    IS_LONG          = "is_long"          # ≥ 200 words
    IS_MULTIPART     = "is_multipart"     # contains numbered parts or bullet points

    # Language signals
    IS_MULTILINGUAL  = "is_multilingual"  # detects mixed scripts
    SCRIPT_ARABIC    = "script_arabic"
    SCRIPT_CJK       = "script_cjk"
    SCRIPT_CYRILLIC  = "script_cyrillic"
    SCRIPT_LATIN     = "script_latin"

    # Tone signals (lightweight heuristics only, not semantic)
    LIKELY_QUESTION  = "likely_question"
    LIKELY_COMMAND   = "likely_command"


@dataclass(frozen=True)
class AnalysisHint:
    hint: HintType
    value: bool | str | float    # depends on hint type
    confidence: float            # 0.0 – 1.0, purely structural


@dataclass(frozen=True)
class AnalysisReport:
    """
    Non-binding structural analysis of the input text.
    Passed as context hints to intent_engine — intent_engine may ignore them.
    Zero execution authority.
    """
    hints: list[AnalysisHint]
    word_count: int
    char_count: int
    dominant_script: str         # "latin" | "cyrillic" | "arabic" | "cjk" | "mixed"
    lightweight: bool = False    # True when produced in DEGRADED_MODE

    def has(self, hint: HintType) -> bool:
        return any(h.hint == hint and h.value for h in self.hints)

    def get(self, hint: HintType) -> AnalysisHint | None:
        return next((h for h in self.hints if h.hint == hint), None)


# ─── REGEX PATTERNS (compiled once at import) ─────────────────────────────────

_RE_CODE_BLOCK   = re.compile(r"```[\s\S]*?```|`[^`\n]+`")
_RE_JSON         = re.compile(r"\{[\s\S]{2,}\}|\[[\s\S]{2,}\]")
_RE_MATH         = re.compile(r"[=∑∫√²³π÷×±≈≠≤≥]|\b\d+[\+\-\*/]\d+")
_RE_URL          = re.compile(r"https?://\S+|www\.\S+")
_RE_LIST_ITEM    = re.compile(r"^\s*[-•*]\s|\b\d+[.)]\s", re.MULTILINE)
_RE_NUMBERED_Q   = re.compile(r"^\s*\d+[.)]\s.+", re.MULTILINE)

# Script detection ranges
_RE_ARABIC    = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_RE_CJK       = re.compile(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF]")
_RE_CYRILLIC  = re.compile(r"[\u0400-\u04FF]")
_RE_LATIN     = re.compile(r"[A-Za-z]")


# ─── SCRIPT DETECTION ─────────────────────────────────────────────────────────

def _detect_scripts(text: str) -> dict[str, int]:
    return {
        "arabic":   len(_RE_ARABIC.findall(text)),
        "cjk":      len(_RE_CJK.findall(text)),
        "cyrillic": len(_RE_CYRILLIC.findall(text)),
        "latin":    len(_RE_LATIN.findall(text)),
    }


def _dominant_script(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "latin"

    dominant = max(counts, key=counts.get)
    dominant_ratio = counts[dominant] / total

    # If dominant script covers < 70% → mixed
    if dominant_ratio < 0.70:
        return "mixed"

    return dominant


# ─── FULL ANALYSIS ────────────────────────────────────────────────────────────

def _full_analysis(text: str) -> AnalysisReport:
    """
    Full structural analysis. Used on ALLOW and HEAVY_REQUIRED.
    No LLM. No I/O. Pure text heuristics.
    """
    words  = text.split()
    word_count = len(words)
    char_count = len(text)

    scripts  = _detect_scripts(text)
    dominant = _dominant_script(scripts)

    hints: list[AnalysisHint] = []

    # ── structural ────────────────────────────────────────────────────────────
    if _RE_CODE_BLOCK.search(text):
        hints.append(AnalysisHint(HintType.HAS_CODE_BLOCK, True, 0.97))

    if _RE_JSON.search(text):
        hints.append(AnalysisHint(HintType.HAS_JSON, True, 0.85))

    if _RE_MATH.search(text):
        hints.append(AnalysisHint(HintType.HAS_MATH, True, 0.80))

    if _RE_URL.search(text):
        hints.append(AnalysisHint(HintType.HAS_URL, True, 0.99))

    if _RE_LIST_ITEM.search(text) or _RE_NUMBERED_Q.search(text):
        hints.append(AnalysisHint(HintType.HAS_LIST, True, 0.90))

    # ── length ────────────────────────────────────────────────────────────────
    if word_count <= 20:
        hints.append(AnalysisHint(HintType.IS_SHORT, True, 1.0))
    elif word_count >= 200:
        hints.append(AnalysisHint(HintType.IS_LONG, True, 1.0))

    # ── multipart ─────────────────────────────────────────────────────────────
    numbered = _RE_NUMBERED_Q.findall(text)
    if len(numbered) >= 2:
        hints.append(AnalysisHint(HintType.IS_MULTIPART, True, 0.88))

    # ── script signals ────────────────────────────────────────────────────────
    if scripts["arabic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_ARABIC, True, 0.99))
    if scripts["cjk"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CJK, True, 0.99))
    if scripts["cyrillic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CYRILLIC, True, 0.99))
    if scripts["latin"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_LATIN, True, 0.99))

    if dominant == "mixed":
        hints.append(AnalysisHint(HintType.IS_MULTILINGUAL, True, 0.85))

    # ── tone heuristics ───────────────────────────────────────────────────────
    stripped = text.strip()
    if stripped.endswith(("?", "؟", "？")):
        hints.append(AnalysisHint(HintType.LIKELY_QUESTION, True, 0.95))

    first_word = words[0].lower().rstrip(".,!?") if words else ""
    command_starters = {
        "write", "make", "create", "generate", "build", "fix", "help",
        "explain", "show", "translate", "convert", "find", "search",
        "напиши", "сделай", "создай", "объясни", "покажи", "найди",
        "переведи", "исправь", "помоги",
    }
    if first_word in command_starters:
        hints.append(AnalysisHint(HintType.LIKELY_COMMAND, True, 0.82))

    return AnalysisReport(
        hints=hints,
        word_count=word_count,
        char_count=char_count,
        dominant_script=dominant,
        lightweight=False,
    )


# ─── LIGHTWEIGHT ANALYSIS (DEGRADED_MODE) ─────────────────────────────────────

def _lightweight_analysis(text: str) -> AnalysisReport:
    """
    Minimal structural analysis for DEGRADED_MODE.
    Only the fastest checks — no regex that scans full text.
    """
    words      = text.split()
    word_count = len(words)
    char_count = len(text)

    hints: list[AnalysisHint] = []

    # Only script detection and length — cheapest possible checks
    scripts  = _detect_scripts(text)
    dominant = _dominant_script(scripts)

    if scripts["arabic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_ARABIC, True, 0.99))
    if scripts["cjk"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CJK, True, 0.99))
    if scripts["cyrillic"] > 0:
        hints.append(AnalysisHint(HintType.SCRIPT_CYRILLIC, True, 0.99))

    if word_count <= 20:
        hints.append(AnalysisHint(HintType.IS_SHORT, True, 1.0))

    if "```" in text:
        hints.append(AnalysisHint(HintType.HAS_CODE_BLOCK, True, 0.95))

    if text.strip().endswith(("?", "؟", "？")):
        hints.append(AnalysisHint(HintType.LIKELY_QUESTION, True, 0.95))

    return AnalysisReport(
        hints=hints,
        word_count=word_count,
        char_count=char_count,
        dominant_script=dominant,
        lightweight=True,
    )


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def analyse(text: str, lightweight: bool = False) -> AnalysisReport:
    """
    Entry point for the meta analysis step.

    Called automatically in the DAG before intent_engine.
    NOT called by Orchestrator.

    Args:
        text:        Raw user input (post safety pass, pre intent classification).
        lightweight: True in DEGRADED_MODE, False otherwise.

    Returns:
        AnalysisReport with structural hints.
        All hints are non-binding — intent_engine may ignore them entirely.

    Never raises. Returns an empty report on any error.
    """
    if not text or not text.strip():
        return AnalysisReport(
            hints=[],
            word_count=0,
            char_count=0,
            dominant_script="latin",
            lightweight=lightweight,
        )

    try:
        if lightweight:
            return _lightweight_analysis(text)
        return _full_analysis(text)
    except Exception:
        # Meta layer must never crash the pipeline
        return AnalysisReport(
            hints=[],
            word_count=len(text.split()),
            char_count=len(text),
            dominant_script="latin",
            lightweight=lightweight,
        )



# memory_audit.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ─── AUDIT FINDING TYPES ──────────────────────────────────────────────────────

class AuditFinding(str, Enum):
    # Memory freshness
    HISTORY_EMPTY        = "history_empty"          # no turns in conversation history
    HISTORY_STALE        = "history_stale"          # last turn older than threshold
    HISTORY_LARGE        = "history_large"          # too many turns (truncation risk)

    # Vector memory
    VECTOR_EMPTY         = "vector_empty"           # no embeddings stored for user
    VECTOR_STALE         = "vector_stale"           # embeddings not updated recently
    VECTOR_POPULATED     = "vector_populated"       # embeddings present and fresh

    # Consistency
    HISTORY_VECTOR_GAP   = "history_vector_gap"     # turns in history but no vectors
    DUPLICATE_TURNS      = "duplicate_turns"        # same content appears multiple times

    # Health
    MEMORY_OK            = "memory_ok"              # no issues found
    MEMORY_DEGRADED      = "memory_degraded"        # partial data available
    MEMORY_UNAVAILABLE   = "memory_unavailable"     # could not inspect memory at all


# ─── INPUT CONTRACT ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MemorySnapshot:
    """
    A read-only snapshot of the user's memory state.
    Populated by whoever calls audit() — typically from memory layer reads.
    memory_audit.py does NOT read memory directly (no I/O).
    """
    user_id: int | None

    # Conversation history
    history_turn_count: int = 0
    history_last_turn_age_seconds: float | None = None  # None = no turns
    history_has_duplicates: bool = False

    # Vector memory
    vector_entry_count: int = 0
    vector_last_updated_age_seconds: float | None = None  # None = never updated

    # Whether the snapshot itself is valid
    snapshot_available: bool = True


# ─── REPORT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditReport:
    """
    Read-only diagnostic report of the memory layer for one user.

    Zero authority — cannot trigger any action.
    May be passed to reflection.py as optional context.
    """
    timestamp_utc: str
    user_id: int | None
    findings: list[AuditFinding]
    history_turn_count: int
    vector_entry_count: int
    notes: list[str] = field(default_factory=list)
    lightweight: bool = False

    def has_finding(self, finding: AuditFinding) -> bool:
        return finding in self.findings

    def is_healthy(self) -> bool:
        return AuditFinding.MEMORY_OK in self.findings

    def to_dict(self) -> dict:
        return {
            "timestamp_utc":      self.timestamp_utc,
            "user_id":            self.user_id,
            "findings":           [f.value for f in self.findings],
            "history_turn_count": self.history_turn_count,
            "vector_entry_count": self.vector_entry_count,
            "notes":              self.notes,
            "lightweight":        self.lightweight,
        }


# ─── THRESHOLDS ───────────────────────────────────────────────────────────────

_HISTORY_STALE_THRESHOLD_S  = 60 * 60 * 24 * 7   # 7 days
_VECTOR_STALE_THRESHOLD_S   = 60 * 60 * 24 * 3    # 3 days
_HISTORY_LARGE_THRESHOLD    = 100                  # turns
_HISTORY_VECTOR_GAP_MIN_TURNS = 5                  # min turns to flag gap


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _collect_findings(snap: MemorySnapshot) -> list[AuditFinding]:
    if not snap.snapshot_available:
        return [AuditFinding.MEMORY_UNAVAILABLE]

    findings: list[AuditFinding] = []

    # ── conversation history ───────────────────────────────────────────────────
    if snap.history_turn_count == 0:
        findings.append(AuditFinding.HISTORY_EMPTY)
    else:
        if snap.history_turn_count >= _HISTORY_LARGE_THRESHOLD:
            findings.append(AuditFinding.HISTORY_LARGE)

        if (
            snap.history_last_turn_age_seconds is not None
            and snap.history_last_turn_age_seconds > _HISTORY_STALE_THRESHOLD_S
        ):
            findings.append(AuditFinding.HISTORY_STALE)

        if snap.history_has_duplicates:
            findings.append(AuditFinding.DUPLICATE_TURNS)

    # ── vector memory ─────────────────────────────────────────────────────────
    if snap.vector_entry_count == 0:
        findings.append(AuditFinding.VECTOR_EMPTY)
    else:
        if (
            snap.vector_last_updated_age_seconds is not None
            and snap.vector_last_updated_age_seconds > _VECTOR_STALE_THRESHOLD_S
        ):
            findings.append(AuditFinding.VECTOR_STALE)
        else:
            findings.append(AuditFinding.VECTOR_POPULATED)

    # ── consistency gap ───────────────────────────────────────────────────────
    if (
        snap.history_turn_count >= _HISTORY_VECTOR_GAP_MIN_TURNS
        and snap.vector_entry_count == 0
    ):
        findings.append(AuditFinding.HISTORY_VECTOR_GAP)

    # ── overall health ────────────────────────────────────────────────────────
    critical = {
        AuditFinding.MEMORY_UNAVAILABLE,
        AuditFinding.HISTORY_VECTOR_GAP,
        AuditFinding.DUPLICATE_TURNS,
    }
    degraded = {
        AuditFinding.HISTORY_STALE,
        AuditFinding.VECTOR_STALE,
        AuditFinding.VECTOR_EMPTY,
        AuditFinding.HISTORY_LARGE,
    }

    found_set = set(findings)
    if found_set & critical:
        findings.append(AuditFinding.MEMORY_DEGRADED)
    elif found_set & degraded:
        findings.append(AuditFinding.MEMORY_DEGRADED)
    elif not found_set - {AuditFinding.HISTORY_EMPTY, AuditFinding.VECTOR_EMPTY}:
        # Only absence findings — new user, not a problem
        findings.append(AuditFinding.MEMORY_OK)
    else:
        findings.append(AuditFinding.MEMORY_OK)

    return findings


def _collect_notes(snap: MemorySnapshot, findings: list[AuditFinding]) -> list[str]:
    """Human-readable observations. Only in full mode."""
    notes: list[str] = []
    found = set(findings)

    if AuditFinding.MEMORY_UNAVAILABLE in found:
        notes.append("Memory snapshot unavailable — audit skipped.")
        return notes

    if AuditFinding.HISTORY_EMPTY in found:
        notes.append("No conversation history — new or reset user.")

    if AuditFinding.HISTORY_LARGE in found:
        notes.append(
            f"History has {snap.history_turn_count} turns "
            f"(threshold: {_HISTORY_LARGE_THRESHOLD}). Truncation risk."
        )

    if AuditFinding.HISTORY_STALE in found:
        days = (snap.history_last_turn_age_seconds or 0) / 86400
        notes.append(f"Last conversation turn was {days:.1f} days ago — stale context.")

    if AuditFinding.DUPLICATE_TURNS in found:
        notes.append("Duplicate turns detected in conversation history.")

    if AuditFinding.VECTOR_EMPTY in found:
        notes.append("No vector embeddings stored for this user.")

    if AuditFinding.VECTOR_STALE in found:
        days = (snap.vector_last_updated_age_seconds or 0) / 86400
        notes.append(f"Vector embeddings not updated for {days:.1f} days.")

    if AuditFinding.HISTORY_VECTOR_GAP in found:
        notes.append(
            f"Gap: {snap.history_turn_count} history turns but no vector embeddings. "
            "Retrieval will be degraded."
        )

    if AuditFinding.MEMORY_OK in found:
        notes.append("Memory state is healthy.")

    return notes


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def audit(snap: MemorySnapshot, lightweight: bool = False) -> AuditReport:
    """
    Produce a read-only diagnostic report of the user's memory state.

    Args:
        snap:        Read-only memory snapshot (populated by caller from memory reads).
        lightweight: True in DEGRADED_MODE — skips note generation.

    Returns:
        AuditReport — pure data, zero side effects.
        May be passed as optional input to reflection.py.
        Never triggers any memory write or execution.

    Never raises. Returns a minimal report on error.
    """
    try:
        findings = _collect_findings(snap)
        notes    = [] if lightweight else _collect_notes(snap, findings)

        return AuditReport(
            timestamp_utc      = _utc_now(),
            user_id            = snap.user_id,
            findings           = findings,
            history_turn_count = snap.history_turn_count,
            vector_entry_count = snap.vector_entry_count,
            notes              = notes,
            lightweight        = lightweight,
        )

    except Exception:
        # Meta layer must never crash the side-channel
        return AuditReport(
            timestamp_utc      = _utc_now(),
            user_id            = getattr(snap, "user_id", None),
            findings           = [AuditFinding.MEMORY_UNAVAILABLE],
            history_turn_count = 0,
            vector_entry_count = 0,
            notes              = ["AuditReport construction failed."],
            lightweight        = lightweight,
        )