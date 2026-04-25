def setup_tracing():
    try:
        from opentelemetry import trace
    except ImportError:
        return