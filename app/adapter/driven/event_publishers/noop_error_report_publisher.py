import structlog

from app.core.application.services.problem_details import ErrorReportPayload

logger = structlog.get_logger()


class NoOpErrorReportPublisher:
    async def publish_error(self, payload: ErrorReportPayload) -> None:
        logger.info(
            "error_report.noop_published",
            classification=payload.classification,
            path=payload.path,
            timestamp=payload.timestamp,
        )
