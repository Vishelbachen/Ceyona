"""
check_imports.py — Architecture layer boundary enforcement
Used by:  CI (architecture job) and pre-commit hook
Source of truth: architecture.md §19 AUTHORITY BOUNDARIES

Run standalone:  python project-root/scripts/check_imports.py
Exit 0 = clean, Exit 1 = violations found
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent  # project-root/

# ─────────────────────────────────────────────────────────────────────────────
# Forbidden import pairs derived from architecture.md §19
# (source_layer_prefix, forbidden_target_prefix)
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN: list[tuple[str, str]] = [
    # Transport must not reach cognition internals
    ("transport", "cognition.reasoning_engine"),
    ("transport", "cognition.multi_agent_coordinator"),
    ("transport", "cognition.response_synthesizer"),
    # Agents must not touch infra or payments
    ("agents", "infra"),
    ("agents", "payments"),
    ("agents", "transport"),
    # Retrieval must not depend on transport or speech
    ("retrieval", "transport"),
    ("retrieval", "external.speech_to_text"),
    ("retrieval", "external.text_to_speech"),
    ("retrieval", "cognition.reasoning_engine"),
    # META layer must never control execution (architecture.md §6)
    ("meta", "core.execution"),
    ("meta", "core.kernel.execution_policy_kernel"),
    ("meta", "core.kernel.decision_matrix"),
    ("meta", "agents.fast_agent"),
    ("meta", "agents.deep_agent"),
    ("meta", "agents.compound_agent"),
    ("meta", "agents.creative_agent"),
    # Observability is read-only (architecture.md §10)
    ("observability", "core.execution"),
    ("observability", "cognition"),
    ("observability", "agents"),
    ("observability", "payments"),
    # Contracts must stay pure — no runtime dependencies
    ("contracts", "transport"),
    ("contracts", "infra"),
    ("contracts", "payments"),
    ("contracts", "agents"),
    ("contracts", "cognition"),
    ("contracts", "retrieval"),
    ("contracts", "external"),
    ("contracts", "memory"),
    ("contracts", "llm"),
    # Infra stays below business logic
    ("infra", "cognition"),
    ("infra", "agents"),
    ("infra", "payments"),
    ("infra", "llm"),
    ("infra", "retrieval"),
    # cost_model ↔ model_router are separate authorities (architecture.md §8)
    ("core.kernel.cost_model", "llm.model_router"),
    ("llm.model_router", "core.kernel.cost_model"),
    # Security layer must not embed business logic
    ("security", "cognition"),
    ("security", "agents"),
    ("security", "payments"),
]


def layer_path(layer: str) -> pathlib.Path:
    return ROOT / layer.replace(".", "/")


def get_imported_module(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else ""
    return ""


def check() -> list[str]:
    errors: list[str] = []

    for source_layer, forbidden_target in FORBIDDEN:
        source_dir = layer_path(source_layer)
        if not source_dir.exists():
            continue

        pattern = "*.py" if source_dir.is_dir() else ""
        files = list(source_dir.rglob("*.py")) if source_dir.is_dir() else [source_dir]

        for py_file in files:
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                errors.append(f"⚠️  SyntaxError in {py_file}: {exc}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = get_imported_module(node)
                    if module.startswith(forbidden_target):
                        rel = py_file.relative_to(ROOT)
                        errors.append(
                            f"❌ FORBIDDEN: {rel}:{node.lineno} — "
                            f"{source_layer} → {forbidden_target}  "
                            f"(imported: {module!r})"
                        )

    return errors


def main() -> int:
    errors = check()
    if errors:
        print("\n🚨 Architecture layer boundary violations:\n")
        for e in errors:
            print(f"  {e}")
        print(f"\n  {len(errors)} violation(s). Fix before pushing.\n")
        return 1

    print("✅ Architecture boundaries OK — all layer contracts respected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())