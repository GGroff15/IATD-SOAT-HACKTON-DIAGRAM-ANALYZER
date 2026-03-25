from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorReportPayload:
    classification: str
    reason: str
    path: str
    timestamp: str
    correlation_id: str | None