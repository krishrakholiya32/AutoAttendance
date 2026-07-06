"""Self-contained OTel setup, deliberately duplicated rather than imported from
backend/ -- face-worker has no shared code with the main API by design (see
app.py's module docstring), same reasoning as liveness.py's own duplication."""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Empty/unset disables exporting entirely -- see backend/app/core/tracing.py's
# docstring for why (Tempo only exists in the Docker Compose stack, not yet on
# the pre-Phase-8 production systemd deploy).
OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")


def configure_tracing(fastapi_app) -> None:
    if OTEL_ENDPOINT:
        provider = TracerProvider(resource=Resource.create({"service.name": "autoattendance-face-worker"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)))
        trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(fastapi_app)
