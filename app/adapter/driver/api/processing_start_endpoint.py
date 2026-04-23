import asyncio
from collections.abc import Awaitable, Callable
from contextvars import copy_context
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from app.adapter.driver.api.problem_details import (
    build_error_report_payload,
    map_exception_to_problem,
)
from app.core.application.ports.error_report_publisher import ErrorReportPublisher
from app.core.domain.entities.diagram_upload import DiagramUpload
from app.infrastructure.logging.correlation import clear_correlation_id, get_correlation_id, set_correlation_id

logger = structlog.get_logger()


class ProcessingStartFileRequest(BaseModel):
    url: str = Field(..., description="HTTP(S) URL for the diagram file")
    mimetype: str = Field(..., min_length=1, description="MIME type of the uploaded diagram")


class ProcessingStartRequest(BaseModel):
    protocol: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    file: ProcessingStartFileRequest


class ProcessingStartResponse(BaseModel):
    status: str
    protocol: str


def _parse_upload_from_url(file_url: str, mimetype: str, protocol: str) -> DiagramUpload:
    normalized_file_url = file_url.strip()
    parsed = urlsplit(normalized_file_url)
    scheme = parsed.scheme.lower()

    if scheme not in {"http", "https"}:
        raise ValueError("file.url must be a valid http(s) URL")

    if not parsed.netloc:
        raise ValueError("file.url must include a host")

    object_key = parsed.path.rsplit("/", 1)[-1]
    suffix_index = object_key.rfind(".")
    extension = object_key[suffix_index:] if suffix_index > -1 else ""

    if not extension:
        mimetype_to_extension = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
        }
        extension = mimetype_to_extension.get(mimetype.lower(), "")

    if not extension:
        raise ValueError("file.url must include an extension or a supported mimetype")

    try:
        diagram_uuid = UUID(protocol)
    except ValueError as exc:
        raise ValueError("protocol must be a valid UUID") from exc

    return DiagramUpload(
        diagram_upload_id=diagram_uuid,
        extension=extension,
        file_url=normalized_file_url,
    )


def create_app(
    processor: Callable[[DiagramUpload], Awaitable[None]],
    error_report_publisher: ErrorReportPublisher,
) -> FastAPI:
    app = FastAPI(title="Diagram Analyzer Service")
    in_flight_tasks: set[asyncio.Task[None]] = set()

    async def _process_upload_in_background(upload: DiagramUpload) -> None:
        try:
            await processor(upload)
        except Exception as exc:
            correlation_id = get_correlation_id()
            problem, classification = map_exception_to_problem(exc=exc, instance="/processing-start")

            logger.exception(
                "http.processing_start.background_failed",
                error_classification=classification,
                path="/processing-start",
                correlation_id=correlation_id,
                status_code=problem.status,
            )

            payload = build_error_report_payload(
                problem=problem,
                classification=classification,
                path="/processing-start",
                correlation_id=correlation_id,
            )

            try:
                await error_report_publisher.publish_error(payload)
            except Exception:
                logger.exception(
                    "http.processing_start.background_error_report_publish_failed",
                    error_classification=classification,
                    path="/processing-start",
                    correlation_id=correlation_id,
                )
        finally:
            clear_correlation_id()

    def _schedule_processing(upload: DiagramUpload) -> None:
        context = copy_context()
        coroutine = _process_upload_in_background(upload)
        try:
            task = context.run(asyncio.create_task, coroutine)
        except Exception:
            coroutine.close()
            raise
        in_flight_tasks.add(task)
        task.add_done_callback(in_flight_tasks.discard)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        problem, classification = map_exception_to_problem(exc=exc, instance=request.url.path)
        correlation_id = get_correlation_id()

        logger.exception(
            "http.processing_start.failed",
            error_classification=classification,
            path=request.url.path,
            correlation_id=correlation_id,
            status_code=problem.status,
        )

        payload = build_error_report_payload(
            problem=problem,
            classification=classification,
            path=request.url.path,
            correlation_id=correlation_id,
        )

        try:
            await error_report_publisher.publish_error(payload)
        except Exception:
            logger.exception(
                "http.processing_start.error_report_publish_failed",
                error_classification=classification,
                path=request.url.path,
                correlation_id=correlation_id,
            )

        return JSONResponse(
            status_code=problem.status,
            content=problem.to_dict(),
            media_type="application/problem+json",
        )

    @app.post(
        "/processing-start",
        response_model=ProcessingStartResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def processing_start(request: ProcessingStartRequest) -> ProcessingStartResponse:
        try:
            upload = _parse_upload_from_url(
                request.file.url,
                request.file.mimetype,
                request.protocol,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

        set_correlation_id(str(upload.diagram_upload_id))
        try:
            logger.info(
                "http.processing_start.accepted",
                protocol=request.protocol,
                file_url=request.file.url,
                diagram_upload_id=str(upload.diagram_upload_id),
            )
            _schedule_processing(upload)
            return ProcessingStartResponse(status="accepted", protocol=request.protocol)
        finally:
            clear_correlation_id()

    return app
