from __future__ import annotations

from typing import Dict, Any

from infra.config_loader import Settings


# =========================
# HEALTH STATUS MODEL
# =========================
class HealthStatus:
    """
    Simple system health representation.
    """

    def __init__(self, ok: bool, details: Dict[str, Any]):
        self.ok = ok
        self.details = details


# =========================
# HEALTHCHECK SERVICE
# =========================
class HealthCheck:
    """
    ROLE:
    - verify system readiness
    - check critical external dependencies availability (logically)
    - provide diagnostic snapshot

    STRICT RULES:
    - no recovery actions
    - no retries
    - no business logic
    - no runtime modification of system state
    """

    def check(self, settings: Settings) -> HealthStatus:

        details: Dict[str, Any] = {}

        # CORE
        details["bot_token"] = self._check_present(settings.BOT_TOKEN)
        details["jwt_secret"] = self._check_present(settings.JWT_SECRET)
        details["encryption_key"] = self._check_present(settings.ENCRYPTION_KEY)

        # LLM
        details["groq_api"] = self._check_present(settings.GROQ_API_KEY)

        # EXTERNAL (optional services)
        details["openweather"] = self._check_present(settings.OPENWEATHER_API_KEY)
        details["mapbox"] = self._check_present(settings.MAPBOX_TOKEN)
        details["serpapi"] = self._check_present(settings.SERPAPI_KEY)

        # STORAGE
        details["redis"] = self._check_present(settings.REDIS_URL)
        details["supabase"] = self._check_present(settings.SUPABASE_URL)

        # SYSTEM HEALTH DECISION
        critical_ok = all([
            details["bot_token"],
            details["jwt_secret"],
            details["encryption_key"],
            details["groq_api"],
        ])

        return HealthStatus(
            ok=critical_ok,
            details=details,
        )

    # =========================
    # INTERNAL CHECK
    # =========================
    def _check_present(self, value: str | None) -> bool:
        return bool(value and len(value.strip()) > 0)