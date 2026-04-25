from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

def setup_tracing():

    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)