import os

def init_sentry():
    try:
        import sentry_sdk
    except ImportError:
        return  # SAFE FAIL (CRITICAL)

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=1.0,
    )