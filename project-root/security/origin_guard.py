from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse


# =========================
# ORIGIN CONTEXT
# =========================
@dataclass
class OriginContext:
    origin: str
    is_allowed: bool
    reason: Optional[str] = None


# =========================
# ORIGIN GUARD (SECURITY LAYER)
# =========================
class OriginGuard:
    """
    ROLE:
    - validate request origin (CORS / webhooks / API ingress)
    - enforce allowed origin whitelist
    - block unauthorized external sources

    DOES NOT:
    - authenticate users
    - rate limit traffic
    - perform encryption
    - influence business logic
    """

    def __init__(self, allowed_origins: List[str]):
        self.allowed_origins = allowed_origins or []

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

        for allowed in self.allowed_origins:

            # wildcard subdomain support
            if allowed.startswith("*."):
                domain = allowed[2:]
                if origin.endswith(domain):
                    return True
                continue

            if origin == allowed:
                return True

        return False

    # =========================
    # NORMALIZATION (STRICT)
    # =========================
    def _normalize(self, origin: str) -> str:

        try:
            parsed = urlparse(origin)

            # always prefer hostname if available
            if parsed.hostname:
                return parsed.hostname.lower().strip()

            return origin.lower().strip()

        except Exception:
            return origin.lower().strip()