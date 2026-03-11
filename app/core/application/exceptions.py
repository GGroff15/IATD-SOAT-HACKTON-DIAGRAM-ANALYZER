class DiagramAnalyzerException(Exception):
    """Base exception for diagram analyzer application errors."""


class InvalidMessageError(DiagramAnalyzerException):
    """Raised when an incoming message is malformed or invalid."""


class ProcessingError(DiagramAnalyzerException):
    """Raised when processing of a valid message fails."""
