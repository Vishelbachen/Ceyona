import logging

from app.settings import settings

logger = logging.getLogger(__name__)


def setup_sentry() -> None:
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not set, skipping")
        return
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init failed", extra={"error": str(exc)})


def capture_exception(exc: Exception, context: dict | None = None) -> None:
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if context:
                for k, v in context.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass