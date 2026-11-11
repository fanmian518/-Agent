from functools import lru_cache
from opentelemetry import trace
from backend.app.infrastructure.settings import RuntimeSettings


@lru_cache(maxsize=1)
def configure_telemetry():
    endpoint = RuntimeSettings().otel_exporter_otlp_endpoint
    if not endpoint:
        return None
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider = TracerProvider(resource=Resource.create({'service.name': 'shopping-langgraph'}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint.rstrip('/') + '/v1/traces')))
    trace.set_tracer_provider(provider)
    return provider


def agent_span():
    configure_telemetry()
    return trace.get_tracer(__name__).start_as_current_span('shopping.agent', record_exception=False)
