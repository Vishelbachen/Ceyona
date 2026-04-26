from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from app.settings import Settings


# =========================
# ORIGIN CONTEXT
# =========================
@dataclass
class OriginContext:
    origin: str
    is_allowed: bool
    reason: Optional[str] = None


# =========================
# ORIGIN GUARD
# =========================
class OriginGuard:
    """
    ROLE:
    - validate request origin (CORS / webhook / API)
    - enforce allowed origins list
    - protect ingress layer from unauthorized sources

    STRICT RULES:
    - no business logic
    - no auth decisions beyond origin validation
    - no dependency on internal systems
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self.allowed_origins = self._load_allowed_origins()

    # =========================
    # LOAD CONFIG
    # =========================
    def _load_allowed_origins(self) -> List[str]:
        origins = self._settings.ALLOWED_ORIGINS

        if not origins:
            return []

        if isinstance(origins, str):
            return [origins]

        return list(origins)

    # =========================
    # VALIDATE ORIGIN
    # =========================
    def validate(self, origin: Optional[str]) -> OriginContext:
        if not origin:
            return OriginContext(
                origin="unknown",
                is_allowed=False,
                reason="missing_origin",
            )

        normalized = self._normalize(origin)

        if self._is_allowed(normalized):
            return OriginContext(
                origin=normalized,
                is_allowed=True,
            )

        return OriginContext(
            origin=normalized,
            is_allowed=False,
            reason="origin_not_allowed",
        )

    # =========================
    # CHECK LOGIC
    # =========================
    def _is_allowed(self, origin: str) -> bool:
        if "*" in self.allowed_origins:
            return True

        if origin in self.allowed_origins:
            return True

        # wildcard subdomains support
        for allowed in self.allowed_origins:
            if allowed.startswith("*."):
                base = allowed[2:]
                if origin.endswith(base):
                    return True

        return False

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize(self, origin: str) -> str:
        try:
            parsed = urlparse(origin)

            if parsed.scheme:
                return parsed.netloc.lower().strip()

            return origin.lower().strip()

        except Exception:
            return origin.lower().strip()