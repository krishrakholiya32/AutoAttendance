from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings


def configure_tracing(service_name: str, fastapi_app=None) -> None:
    """Sets up an OTLP-exporting tracer for this process (API or arq worker)
    so a single request's trace can be viewed end to end in Tempo.
    `fastapi_app` is only passed by processes that serve HTTP (the API) --
    the arq worker has no ASGI app to instrument but still needs a configured
    tracer so `tracer.start_as_current_span(...)` calls in the task code export
    correctly.

    Tempo only exists in the Docker Compose stack (Phase 7+8); on the
    pre-Compose production systemd deploy, `otel_exporter_otlp_endpoint` is
    left unset in .env so this skips exporter setup entirely rather than
    spamming the log with connection-refused retries against a host that
    doesn't exist there yet."""
    if settings.otel_exporter_otlp_endpoint:
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True))
        )
        trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()

    if fastapi_app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(fastapi_app)
