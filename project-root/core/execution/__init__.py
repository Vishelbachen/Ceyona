"""
core/execution — public API facade.

External callers (transport/, tests, future CLI/REST) import from here.
They don't need to know which file inside core/execution owns the implementation.

If orchestrator.py is split into runner.py + request.py + result.py tomorrow,
no external import changes.

Public API:
  run()                — execute the full orchestration pipeline
  OrchestratorRequest  — input contract (transport → orchestrator)
  OrchestratorResult   — output contract (orchestrator → transport)
  UsageRecord          — billing record carried on OrchestratorResult

NOT re-exported (internal):
  PipelineMetrics, CoordinationMetrics, _run_heavy, _build_context, ...
"""
from core.execution.orchestrator import (
    OrchestratorRequest,
    OrchestratorResult,
    UsageRecord,
    run,
)

__all__ = [
    "run",
    "OrchestratorRequest",
    "OrchestratorResult",
    "UsageRecord",
]