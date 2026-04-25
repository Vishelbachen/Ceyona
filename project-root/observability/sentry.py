import sentry_sdk
from app.settings import settings

def init_sentry():
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0
    )