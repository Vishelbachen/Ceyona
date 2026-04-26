from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from infra.config_loader import get_settings


settings = get_settings()


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
    Origin validation layer

    ROLE:
    - validate request origin (CORS / webhook / API calls)
    - enforce allowed domains list
    - prevent unauthorized external sources

    DOES NOT:
    - authenticate user
    - rate limit
    - encrypt data
    - influence business logic
    """

    def __init__(self):
        self.allowed_origins = self._load_allowed_origins()

    # =========================
    # LOAD CONFIG
    # =========================
    def _load_allowed_origins(self) -> List[str]:

        origins = settings.ALLOWED_ORIGINS

        # normalize
        if isinstance(origins, str):
            return [origins]

        return list(origins or [])

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

        # exact match
        if origin in self.allowed_origins:
            return True

        # optional wildcard support (future-safe)
        for allowed in self.allowed_origins:
            if allowed == "*":
                return True

            if allowed.startswith("*."):
                domain = allowed[2:]
                if origin.endswith(domain):
                    return True

        return False

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize(self, origin: str) -> str:

        try:
            parsed = urlparse(origin)

            # fallback for raw domains
            if not parsed.scheme:
                return origin.lower().strip()

            return parsed.netloc.lower().strip()

        except Exception:
            return origin.lower().strip()