from __future__ import annotations

from typing import List, Dict, Any

from infra.config_loader import Settings


# =========================
# REQUIRED ENV RULES
# =========================
REQUIRED_FIELDS = [
    "BOT_TOKEN",
    "JWT_SECRET",
    "ENCRYPTION_KEY",
    "GROQ_API_KEY",
]


# =========================
# ENV VALIDATION ERROR
# =========================
class EnvValidationError(Exception):
    pass


# =========================
# ENV VALIDATOR
# =========================
class EnvValidator:
    """
    ROLE:
    - validate system-critical environment variables at startup
    - fail fast if core configuration is missing

    STRICT RULES:
    - no mutation of settings
    - no runtime fallback logic
    - no business logic
    """

    def validate(self, settings: Settings) -> None:

        missing = self._check_required(settings)

        if missing:
            raise EnvValidationError(
                f"Missing required environment variables: {missing}"
            )

        self._validate_security_keys(settings)

    # =========================
    # REQUIRED CHECK
    # =========================
    def _check_required(self, settings: Settings) -> List[str]:

        missing = []

        for field in REQUIRED_FIELDS:
            value = getattr(settings, field, None)

            if not value:
                missing.append(field)

        return missing

    # =========================
    # SECURITY VALIDATION
    # =========================
    def _validate_security_keys(self, settings: Settings) -> None:

        # JWT_SECRET minimal sanity check
        if len(settings.JWT_SECRET) < 16:
            raise EnvValidationError("JWT_SECRET too weak (min 16 chars)")

        # ENCRYPTION_KEY basic sanity check
        if len(settings.ENCRYPTION_KEY) < 20:
            raise EnvValidationError("ENCRYPTION_KEY too weak or invalid")

        # BOT_TOKEN sanity
        if ":" not in settings.BOT_TOKEN:
            raise EnvValidationError("BOT_TOKEN format invalid")