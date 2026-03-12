from typing import Protocol

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import DetectedConnection


class ConnectionDetector(Protocol):
    """Port for connection detection operations (driven adapter interface)."""

    def detect(
        self,
        image_bytes: bytes,
        components: tuple[DetectedComponent, ...],
    ) -> tuple[DetectedConnection, ...]:
        """Detect connections (lines, arrows) between components in a diagram image.

        Args:
            image_bytes: PNG image content as bytes
            components: Tuple of detected components to use as context for linking connections

        Returns:
            Tuple of DetectedConnection objects representing lines, arrows, and other
            connections found in the diagram. Connections may reference source and target
            components based on proximity analysis.

        Raises:
            ConnectionDetectionError: If the connection detection operation fails
        """
        ...
