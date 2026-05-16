import logging
import structlog
from .correlation import get_correlation_id


def _add_correlation_id(logger, method_name, event_dict):
    cid = get_correlation_id()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _add_trace_context(logger, method_name, event_dict):
    try:
        from opentelemetry import trace

        span_context = trace.get_current_span().get_span_context()
    except Exception:
        return event_dict

    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")

    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_correlation_id,
            _add_trace_context,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
