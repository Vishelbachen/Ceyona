from typing import List, Dict, Optional


class OriginGuard:
    """
    AI Platform v4.7 — Origin Guard

    RESPONSIBILITY:
    - Validate request origin against allowlist
    - Block unauthorized sources at network boundary
    - Provide deterministic origin filtering

    STRICT RULES:
    - No behavioral analysis
    - No risk scoring
    - No LLM / retrieval / memory usage
    - No orchestrator interaction
    - No dynamic policy decisions
    """

    def __init__(self, allowed_origins: Optional[List[str]] = None):
        self.allowed_origins = allowed_origins or []

    def is_allowed(self, origin: str) -> bool:
        """
        Checks whether origin is in allowlist.
        """

        if not self.allowed_origins:
            return True  # open mode if not configured

        return origin in self.allowed_origins

    def validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Extracts origin and validates it.
        """

        origin = request.get("headers", {}).get("Origin")

        if not origin:
            return False

        return self.is_allowed(origin)

    def add_allowed_origin(self, origin: str) -> None:
        """
        Adds origin to allowlist.
        """

        if origin not in self.allowed_origins:
            self.allowed_origins.append(origin)