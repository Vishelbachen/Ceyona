"""
test_architecture_contracts.py — Static architecture boundary verification
Runs the same checks as CI's architecture job, but as pytest tests
so they show up in coverage and test reports.

These catch: circular deps indicators, forbidden imports, layer leakage.
No live services needed — pure AST analysis.
"""

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).parent.parent


# ─── Helpers ─────────────────────────────────────────────────────────────────

def imports_in_file(path: pathlib.Path) -> list[tuple[str, int]]:
    """Return (module_name, line_number) for all imports in a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            result.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result.append((alias.name, node.lineno))
    return result


def files_in_layer(layer: str) -> list[pathlib.Path]:
    p = ROOT / layer.replace(".", "/")
    if p.is_dir():
        return list(p.rglob("*.py"))
    if p.with_suffix(".py").exists():
        return [p.with_suffix(".py")]
    return []


# ─── Forbidden import pairs (from architecture.md §19) ───────────────────────

FORBIDDEN_PAIRS: list[tuple[str, str, str]] = [
    # (source, forbidden_target, reason)
    ("transport", "cognition.reasoning_engine",        "§3 Layer 5: runtime obeys arch"),
    ("transport", "cognition.multi_agent_coordinator", "§3 Layer 5: runtime obeys arch"),
    ("transport", "cognition.response_synthesizer",    "§3 Layer 5: runtime obeys arch"),
    ("agents",    "infra",                             "§25: agents are execution participants"),
    ("agents",    "payments",                          "§25: agents are execution participants"),
    ("agents",    "transport",                         "§25: agents are execution participants"),
    ("meta",      "core.execution",                    "§6: META never reroutes execution"),
    ("meta",      "core.kernel.execution_policy_kernel", "§6: META never escalates tiers"),
    ("meta",      "core.kernel.decision_matrix",       "§6: META never escalates tiers"),
    ("retrieval", "transport",                         "§3 Layer 3: retrieval is grounding"),
    ("retrieval", "external.speech_to_text",           "§3 Layer 3: retrieval is grounding"),
    ("retrieval", "cognition.reasoning_engine",        "§3 Layer 3: retrieval is grounding"),
    ("contracts", "transport",                         "contracts must stay pure"),
    ("contracts", "agents",                            "contracts must stay pure"),
    ("contracts", "payments",                          "contracts must stay pure"),
    ("observability", "core.execution",                "observability is read-only"),
    ("observability", "cognition",                     "observability is read-only"),
    ("observability", "agents",                        "observability is read-only"),
    ("infra",     "cognition",                         "infra below business logic"),
    ("infra",     "agents",                            "infra below business logic"),
    ("infra",     "payments",                          "infra below business logic"),
    ("core.kernel.cost_model", "llm.model_router",     "§8: separate authorities"),
    ("llm.model_router", "core.kernel.cost_model",     "§8: separate authorities"),
]


@pytest.mark.parametrize("source,forbidden,reason", FORBIDDEN_PAIRS)
def test_forbidden_import(source: str, forbidden: str, reason: str):
    """Each forbidden pair is a separate test — failures are individually visible."""
    violations = []
    for py_file in files_in_layer(source):
        for module, lineno in imports_in_file(py_file):
            if module.startswith(forbidden):
                rel = py_file.relative_to(ROOT)
                violations.append(f"{rel}:{lineno} imports {module!r}")

    assert not violations, (
        f"Architecture violation ({reason}):\n"
        + "\n".join(f"  ❌ {v}" for v in violations)
    )


# ─── Critical module existence ────────────────────────────────────────────────

REQUIRED_MODULES = [
    # architecture.md §4 execution lifecycle — every stage must have a file
    "core/kernel/execution_policy_kernel.py",
    "core/kernel/cost_model.py",
    "core/kernel/decision_matrix.py",
    "core/kernel/policy_registry.py",
    "core/execution/orchestrator.py",
    "cognition/intent_engine.py",
    "cognition/response_synthesizer.py",
    "cognition/multi_agent_coordinator.py",
    "meta/reflection.py",
    "meta/correction.py",
    "meta/output_normalizer.py",
    "meta/analysis.py",
    "meta/memory_audit.py",
    "retrieval/retrieval_engine.py",
    "retrieval/source_credibility.py",
    "contracts/shared_types.py",
    "observability/metrics.py",
    "observability/tracing.py",
    "infra/healthcheck.py",
    "security/safety_gate.py",
]


@pytest.mark.parametrize("module_path", REQUIRED_MODULES)
def test_required_module_exists(module_path: str):
    """Every module declared in architecture.md must exist on disk."""
    full = ROOT / module_path
    assert full.exists(), (
        f"Required module missing: {module_path}\n"
        f"  This module is declared in architecture.md but not found at {full}"
    )


# ─── Safety gate non-blocking invariant (static) ─────────────────────────────

def test_safety_gate_never_raises_deny_statically():
    """
    architecture.md §21: Safety Gate Pass 1/2 are NON-BLOCKING.
    safety_gate.py must not contain a hard 'return DENY' or 'raise' on gate result.
    This is a static heuristic check — not exhaustive but catches accidental regressions.
    """
    safety_gate = ROOT / "security" / "safety_gate.py"
    if not safety_gate.exists():
        pytest.skip("safety_gate.py not found")

    source = safety_gate.read_text(encoding="utf-8")

    # These patterns would indicate safety gate is blocking (forbidden by architecture)
    blocking_patterns = [
        "EPKDecision.DENY",
        "return DENY",
        'raise.*[Uu]nsafe',
    ]

    import re
    found = []
    for pattern in blocking_patterns:
        if re.search(pattern, source):
            found.append(pattern)

    assert not found, (
        f"safety_gate.py may be blocking (architecture.md §21 violation):\n"
        f"  Found patterns: {found}\n"
        f"  Safety Gate must be observability-only (non-blocking).\n"
        f"  Sole blocking authority: safety_agent (post-reasoning)."
    )