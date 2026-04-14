from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.core.application.exceptions import (
    ArchitecturalValidationExecutionError,
    ConnectionDetectionError,
    DiagramDetectionError,
    FileNotFoundError,
    FileStorageError,
    ImageConversionError,
    InvalidMessageError,
    ProcessingError,
    TextExtractionError,
    UnsupportedFileFormatError,
)
from app.core.application.ports.error_report_payload import ErrorReportPayload

URN_NAMESPACE = "urn:diagram-analyzer:error"
FALLBACK_PROBLEM_TYPE = f"{URN_NAMESPACE}:internal"


@dataclass(frozen=True)
class ProblemDetails:
    type: str
    title: str
    status: int
    detail: str
    instance: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProblemMapping:
    status: int
    title: str
    classification: str
    detail: str

    @property
    def problem_type(self) -> str:
        return f"{URN_NAMESPACE}:{self.classification}"


KNOWN_EXCEPTION_MAPPINGS: dict[type[Exception], ProblemMapping] = {
    InvalidMessageError: ProblemMapping(
        status=400,
        title="Invalid Message",
        classification="invalid-message",
        detail="The incoming message is invalid.",
    ),
    ProcessingError: ProblemMapping(
        status=422,
        title="Processing Error",
        classification="processing-error",
        detail="Unable to process the provided diagram.",
    ),
    FileNotFoundError: ProblemMapping(
        status=404,
        title="File Not Found",
        classification="file-not-found",
        detail="Requested file was not found.",
    ),
    FileStorageError: ProblemMapping(
        status=503,
        title="File Storage Error",
        classification="file-storage-error",
        detail="File storage is currently unavailable.",
    ),
    ImageConversionError: ProblemMapping(
        status=422,
        title="Image Conversion Error",
        classification="image-conversion-error",
        detail="Unable to convert file to image format.",
    ),
    UnsupportedFileFormatError: ProblemMapping(
        status=415,
        title="Unsupported File Format",
        classification="unsupported-file-format",
        detail="The provided file format is not supported.",
    ),
    DiagramDetectionError: ProblemMapping(
        status=500,
        title="Diagram Detection Error",
        classification="diagram-detection-error",
        detail="Unable to detect diagram components.",
    ),
    ConnectionDetectionError: ProblemMapping(
        status=500,
        title="Connection Detection Error",
        classification="connection-detection-error",
        detail="Unable to detect diagram connections.",
    ),
    TextExtractionError: ProblemMapping(
        status=502,
        title="Text Extraction Error",
        classification="text-extraction-error",
        detail="Unable to extract text from the diagram.",
    ),
    ArchitecturalValidationExecutionError: ProblemMapping(
        status=500,
        title="Architectural Validation Error",
        classification="architectural-validation-error",
        detail="Unable to validate architectural rules for the generated graph.",
    ),
}


def map_exception_to_problem(exc: Exception, instance: str) -> tuple[ProblemDetails, str]:
    for exception_type, mapping in KNOWN_EXCEPTION_MAPPINGS.items():
        if isinstance(exc, exception_type):
            return (
                ProblemDetails(
                    type=mapping.problem_type,
                    title=mapping.title,
                    status=mapping.status,
                    detail=mapping.detail,
                    instance=instance,
                ),
                mapping.classification,
            )

    return (
        ProblemDetails(
            type=FALLBACK_PROBLEM_TYPE,
            title="Internal Server Error",
            status=500,
            detail="An unexpected error occurred.",
            instance=instance,
        ),
        "internal",
    )


def build_error_report_payload(
    problem: ProblemDetails,
    classification: str,
    path: str,
    correlation_id: str | None,
) -> ErrorReportPayload:
    return ErrorReportPayload(
        classification=classification,
        reason=problem.detail,
        path=path,
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
    )