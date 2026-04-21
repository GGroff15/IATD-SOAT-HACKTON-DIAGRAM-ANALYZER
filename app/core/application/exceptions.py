class DiagramAnalyzerException(Exception):
    """Base exception for diagram analyzer application errors."""


class InvalidMessageError(DiagramAnalyzerException):
    """Raised when an incoming message is malformed or invalid."""


class ProcessingError(DiagramAnalyzerException):
    """Raised when processing of a valid message fails."""


class FileNotFoundError(DiagramAnalyzerException):
    """Raised when a file cannot be found in storage."""


class FileStorageError(DiagramAnalyzerException):
    """Raised when a file storage operation fails."""


class ImageConversionError(DiagramAnalyzerException):
    """Raised when image conversion fails."""


class UnsupportedFileFormatError(DiagramAnalyzerException):
    """Raised when a file format is not supported for conversion."""


class DiagramDetectionError(DiagramAnalyzerException):
    """Raised when diagram component detection fails."""


class ConnectionDetectionError(DiagramAnalyzerException):
    """Raised when connection detection fails."""


class TextExtractionError(DiagramAnalyzerException):
    """Raised when text extraction from image fails."""


class ArchitecturalValidationExecutionError(DiagramAnalyzerException):
    """Raised when architectural validation fails due to a technical/runtime error."""


class LlmInferenceError(DiagramAnalyzerException):
    """Raised when LLM inference fails due to request/response/runtime issues."""
