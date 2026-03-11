from typing import Protocol
from uuid import UUID

from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


class DiagramDetector(Protocol):
    """Port for diagram component detection operations (driven adapter interface)."""

    def detect(self, diagram_upload_id: UUID, image_bytes: bytes) -> DiagramAnalysisResult:
        """Detect components in a diagram image.

        Args:
            diagram_upload_id: UUID of the diagram being analyzed
            image_bytes: PNG image content as bytes

        Returns:
            DiagramAnalysisResult containing detected components with bounding boxes,
            class names, and confidence scores

        Raises:
            DiagramDetectionError: If the detection operation fails
        """
        ...
