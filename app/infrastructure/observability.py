from __future__ import annotations

import json
import logging
import os
import time

from fastapi import FastAPI, Request

LOGGER = logging.getLogger(__name__)
REQUEST_LOGGER = logging.getLogger("soat.request")


def _format_trace_id(trace_id: int) -> str:
    return format(trace_id, "032x")


def _format_span_id(span_id: int) -> str:
    return format(span_id, "016x")


def configure_observability(app: FastAPI) -> None:
    """Configure OpenTelemetry exporters when OTLP is enabled."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        LOGGER.exception("otel.dependencies_unavailable")
        return

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", app.title),
            "service.namespace": "soat",
            "deployment.environment": "local",
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider))

    _install_request_logging(app, trace)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()


def _install_request_logging(app: FastAPI, trace) -> None:
    if getattr(app.state, "otel_request_logging_enabled", False):
        return

    app.state.otel_request_logging_enabled = True
    REQUEST_LOGGER.setLevel(logging.INFO)

    @app.middleware("http")
    async def log_http_request(request: Request, call_next):
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_record: dict[str, object] = {
                "event": "http.request",
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }

            span_context = trace.get_current_span().get_span_context()
            if span_context.is_valid:
                log_record["trace_id"] = _format_trace_id(span_context.trace_id)
                log_record["span_id"] = _format_span_id(span_context.span_id)

            REQUEST_LOGGER.info(json.dumps(log_record, separators=(",", ":")))
