import sentry_sdk
from app.settings import settings

def init_sentry():
    sentry_sdk.init(dsn=settings.SENTRY_DSN)