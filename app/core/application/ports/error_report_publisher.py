from typing import Protocol

from app.core.application.ports.error_report_payload import ErrorReportPayload


class ErrorReportPublisher(Protocol):
    async def publish_error(self, payload: ErrorReportPayload) -> None:
        """Publish sanitized error report payload to an asynchronous channel."""
