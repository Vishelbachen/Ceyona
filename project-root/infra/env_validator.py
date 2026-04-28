from typing import Any, Dict, List, Optional
import re


class EnvValidator:
    """
    AI Platform v4.7 — Environment Validator

    RESPONSIBILITY:
    - Validate presence of required environment variables
    - Perform basic format validation (syntax-level only)
    - Ensure runtime config completeness

    STRICT RULES:
    - No business logic validation
    - No feature flag interpretation
    - No security decisions
    - No LLM / retrieval / memory usage
    - No orchestration influence
    """

    def __init__(self):
        self._errors: List[str] = []

    def validate_required(self, env: Dict[str, Optional[str]], required_keys: List[str]) -> bool:
        """
        Checks that all required environment variables exist.
        """

        self._errors.clear()

        for key in required_keys:
            if not env.get(key):
                self._errors.append(f"Missing required env var: {key}")

        return len(self._errors) == 0

    def validate_format(self, key: str, value: Optional[str], pattern: str) -> bool:
        """
        Validates value against regex pattern (syntactic only).
        """

        if value is None:
            self._errors.append(f"{key} is None")
            return False

        if not re.match(pattern, value):
            self._errors.append(f"{key} has invalid format")

            return False

        return True

    def get_errors(self) -> List[str]:
        """
        Returns validation errors.
        """

        return self._errors