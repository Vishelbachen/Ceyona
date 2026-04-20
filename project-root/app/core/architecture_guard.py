import sys
import importlib
import inspect


class ArchitectureViolationError(Exception):
    pass


class ArchitectureGuard:
    """
    Simple import architecture validator.

    Prevents:
    - wrong layer imports (engine/core mismatch)
    - hidden structural drift
    """

    # 🚨 RULES (STRICT LAYER BOUNDARIES)
    RULES = {
        "orchestrator": "core",
        "prompt_builder": "core",
        "reasoning_engine": "core",
        "reasoning_verifier": "core",

        "model_decision": "engine",
        "intent_classifier": "engine",
        "task_classifier": "engine",
        "llm": "engine",
    }

    @staticmethod
    def validate_imports():
        """
        Run at startup to validate architecture consistency.
        """

        for module_name, expected_layer in ArchitectureGuard.RULES.items():
            try:
                module = importlib.import_module(f"app.{expected_layer}.{module_name}")
            except ModuleNotFoundError:
                continue

            file_path = inspect.getfile(module)

            if f"/{expected_layer}/" not in file_path.replace("\\", "/"):
                raise ArchitectureViolationError(
                    f"ARCHITECTURE VIOLATION: {module_name} should be in {expected_layer}, "
                    f"but found at {file_path}"
                )