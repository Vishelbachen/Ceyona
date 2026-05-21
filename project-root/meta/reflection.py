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