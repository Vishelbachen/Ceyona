from typing import Any, Dict, Optional
import os


class ConfigLoader:
    """
    AI Platform v4.7 — Configuration Loader

    RESPONSIBILITY:
    - Load environment variables
    - Provide structured config access
    - Serve static runtime configuration

    STRICT RULES:
    - No validation business logic
    - No decision-making
    - No feature toggling intelligence
    - No LLM / retrieval / memory usage
    - No orchestration influence
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Returns environment variable value.
        """

        if key in self._cache:
            return self._cache[key]

        value = os.getenv(key, default)

        self._cache[key] = value

        return value

    def require(self, key: str) -> str:
        """
        Requires environment variable to exist.
        """

        value = self.get(key)

        if value is None:
            raise EnvironmentError(f"Missing required env var: {key}")

        return value

    def load_all(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """
        Loads multiple environment variables at once.
        """

        return {key: self.get(key) for key in keys}