import logging

from app.settings import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not set, skipping")
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        logger.info("Sentry initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed")