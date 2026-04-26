from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import time
import jwt


# =========================
# CONTEXT OBJECT
# =========================
@dataclass
class AuthContext:
    user_id: str
    is_authenticated: bool
    roles: List[str]
    metadata: Dict[str, Any]


# =========================
# AUTH SERVICE
# =========================
class AuthService:
    """
    Authentication + identity layer

    ROLE:
    - verify JWT tokens
    - validate identity claims
    - extract safe auth context

    DOES NOT:
    - execute business logic
    - interact with LLM / agents / memory
    - make authorization decisions beyond identity parsing
    """

    REQUIRED_CLAIMS = {"sub", "iat", "exp"}

    def __init__(self, jwt_secret: str, algorithm: str = "HS256"):
        self.secret = jwt_secret
        self.algorithm = algorithm

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

            if not self._validate_payload(payload):
                return None

            return self._build_context(payload)

        except jwt.ExpiredSignatureError:
            return None

        except jwt.InvalidTokenError:
            return None

    # =========================
    # PAYLOAD VALIDATION
    # =========================
    def _validate_payload(self, payload: Dict[str, Any]) -> bool:

        # must contain required claims
        if not self.REQUIRED_CLAIMS.issubset(payload.keys()):
            return False

        # type safety checks
        if not isinstance(payload.get("sub"), str):
            return False

        if not isinstance(payload.get("roles", []), list):
            return False

        return True

    # =========================
    # BUILD CONTEXT
    # =========================
    def _build_context(self, payload: Dict[str, Any]) -> AuthContext:

        roles = payload.get("roles", [])
        roles = [str(r).lower() for r in roles]

        return AuthContext(
            user_id=payload["sub"],
            is_authenticated=True,
            roles=roles,
            metadata={
                "issued_at": payload["iat"],
                "expires_at": payload["exp"],
                "verified_at": int(time.time()),
            },
        )

    # =========================
    # ISSUE TOKEN
    # =========================
    def issue_token(
        self,
        user_id: str,
        roles: Optional[List[str]] = None,
        ttl_seconds: int = 3600,
    ) -> str:

        now = int(time.time())

        payload = {
            "sub": user_id,
            "roles": [r.lower() for r in (roles or [])],
            "iat": now,
            "exp": now + ttl_seconds,
        }

        return jwt.encode(
            payload,
            self.secret,
            algorithm=self.algorithm,
        )