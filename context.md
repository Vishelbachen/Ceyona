# analysis.py



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