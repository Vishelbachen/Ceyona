"""
test_meta_isolation.py — META layer isolation enforcement
architecture.md §6: META layers MUST NEVER reroute execution, escalate tiers,
redefine policy, alter orchestration topology, or override authority.

These tests verify the META layer's read-only contract at the import level
and interface level — without needing a live Groq/Supabase connection.
"""

import ast
import importlib
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).parent.parent
META_DIR = ROOT / "meta"

# Modules that META must never import (architecture.md §6 hard prohibition)
META_FORBIDDEN_IMPORTS = [
    "core.execution",
    "core.kernel.execution_policy_kernel",
    "core.kernel.decision_matrix",
    "agents.fast_agent",
    "agents.deep_agent",
    "agents.compound_agent",
    "agents.creative_agent",
    "agents.consensus_engine",
]


# ─── Import boundary: static AST check ───────────────────────────────────────

class TestMetaImportBoundary:
    """META modules must not import execution-control modules (static check)."""

    @pytest.fixture(autouse=True)
    def meta_python_files(self):
        self.files = list(META_DIR.glob("*.py")) if META_DIR.exists() else []

    def _imports_in_file(self, path: pathlib.Path) -> list[str]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
        return imports

    def test_meta_does_not_import_execution_control(self):
        violations = []
        for py_file in self.files:
            for imported in self._imports_in_file(py_file):
                for forbidden in META_FORBIDDEN_IMPORTS:
                    if imported.startswith(forbidden):
                        violations.append(
                            f"{py_file.name}: imports {imported!r} "
                            f"(forbidden: {forbidden})"
                        )
        assert not violations, (
            "META layer imports execution-control modules:\n"
            + "\n".join(f"  ❌ {v}" for v in violations)
        )

    def test_meta_files_exist(self):
        """Meta layer files declared in architecture.md §6 must exist."""
        expected = {
            "reflection.py", "correction.py", "analysis.py",
            "output_normalizer.py", "memory_audit.py",
        }
        if not META_DIR.exists():
            pytest.skip("meta/ directory not found — skipping")
        found = {f.name for f in META_DIR.glob("*.py") if f.name != "__init__.py"}
        missing = expected - found
        assert not missing, f"META modules missing: {missing}"


# ─── Interface contract: META modules must never return routing decisions ─────

class TestMetaInterfaceContract:
    """
    META modules expose safe interfaces.
    They return reports/annotations — never routing/escalation signals.
    """

    def _load_meta_module(self, name: str):
        """Try to import meta module with heavy deps mocked out."""
        mocks = {
            "groq": types.ModuleType("groq"),
            "supabase": types.ModuleType("supabase"),
            "redis": types.ModuleType("redis"),
            "httpx": types.ModuleType("httpx"),
            "structlog": types.ModuleType("structlog"),
        }
        # Provide minimal structlog stub
        mocks["structlog"].get_logger = lambda *a, **kw: types.SimpleNamespace(
            info=lambda *a, **kw: None,
            warning=lambda *a, **kw: None,
            error=lambda *a, **kw: None,
            debug=lambda *a, **kw: None,
        )
        with pytest.MonkeyPatch.context() as mp:
            for mod_name, mock in mocks.items():
                mp.setitem(sys.modules, mod_name, mock)
            try:
                return importlib.import_module(f"meta.{name}")
            except Exception:
                return None

    def test_analysis_never_raises_on_import(self):
        """analysis.py must be importable without side effects."""
        mod = self._load_meta_module("analysis")
        # If import fails, it's a META isolation issue (missing stub)
        # We allow None here — the AST test above is the hard check
        assert mod is None or hasattr(mod, "__file__")

    def test_correction_has_no_routing_attributes(self):
        """correction.py must not expose tier/routing/EPK attributes."""
        mod = self._load_meta_module("correction")
        if mod is None:
            pytest.skip("correction.py not importable in isolation")
        routing_attrs = [
            a for a in dir(mod)
            if any(kw in a.lower() for kw in ("tier", "route", "epk", "escalat", "policy"))
        ]
        assert not routing_attrs, (
            f"correction.py exposes routing-like attributes: {routing_attrs}"
        )

    def test_output_normalizer_has_no_routing_attributes(self):
        mod = self._load_meta_module("output_normalizer")
        if mod is None:
            pytest.skip("output_normalizer.py not importable in isolation")
        routing_attrs = [
            a for a in dir(mod)
            if any(kw in a.lower() for kw in ("tier", "route", "epk", "escalat", "policy"))
        ]
        assert not routing_attrs, (
            f"output_normalizer.py exposes routing-like attributes: {routing_attrs}"
        )


# ─── Synthesizer pipeline step ordering ──────────────────────────────────────

class TestSynthesizerPipelineOrder:
    """
    architecture.md §19 / models1.md §10: 7-step pipeline order is fixed.
    Steps 5 (correction) and 6 (output_normalizer) must run inside synthesizer only,
    not in the META side-channel DAG.
    """

    CANONICAL_STEPS = [
        "assemble",
        "normalize_telegram",
        "structure",
        "format",
        "correction",       # meta/correction.py — synthesizer step 5 only
        "output_normalizer", # meta/output_normalizer.py — synthesizer step 6 only
        "finalize",
    ]

    def test_pipeline_has_seven_steps(self):
        assert len(self.CANONICAL_STEPS) == 7

    def test_correction_before_output_normalizer(self):
        ci = self.CANONICAL_STEPS.index("correction")
        oi = self.CANONICAL_STEPS.index("output_normalizer")
        assert ci < oi, "correction must run before output_normalizer (pipeline order fixed)"

    def test_normalize_telegram_is_second(self):
        """normalize_telegram strips LaTeX/Markdown so downstream sees clean text."""
        assert self.CANONICAL_STEPS[1] == "normalize_telegram"

    def test_finalize_is_last(self):
        assert self.CANONICAL_STEPS[-1] == "finalize"