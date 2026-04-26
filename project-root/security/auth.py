from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import jwt

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# CONTEXT OBJECT
# =========================
@dataclass
class AuthContext:
    user_id: str
    is_authenticated: bool
    roles: list[str]
    metadata: Dict[str, Any]


# =========================
# AUTH SERVICE
# =========================
class AuthService:
    """
    Authentication + identity layer

    ROLE:
    - verify JWT tokens
    - extract identity context
    - attach roles/claims
    - provide safe auth context for pipeline

    DOES NOT:
    - make authorization decisions beyond identity
    - access business logic
    - interact with LLM / agents / memory
    """

    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = "HS256"

    # =========================
    # VERIFY TOKEN
    # =========================
    def verify_token(self, token: str) -> Optional[AuthContext]:

        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )

            return self._build_context(payload)

        except jwt.ExpiredSignatureError:
            return None

        except jwt.InvalidTokenError:
            return None

    # =========================
    # BUILD CONTEXT
    # =========================
    def _build_context(self, payload: Dict[str, Any]) -> AuthContext:

        return AuthContext(
            user_id=payload.get("sub", "anonymous"),
            is_authenticated=True,
            roles=payload.get("roles", []),
            metadata={
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "verified_at": int(time.time()),
            },
        )

    # =========================
    # OPTIONAL: ISSUE TOKEN (SERVICE SIDE)
    # =========================
    def issue_token(
        self,
        user_id: str,
        roles: Optional[list[str]] = None,
        ttl_seconds: int = 3600,
    ) -> str:

        now = int(time.time())

        payload = {
            "sub": user_id,
            "roles": roles or [],
            "iat": now,
            "exp": now + ttl_seconds,
        }

        return jwt.encode(
            payload,
            self.secret,
            algorithm=self.algorithm,
        )