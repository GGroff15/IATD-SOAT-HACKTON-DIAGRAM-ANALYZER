from dataclasses import dataclass, field
from uuid import UUID

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import DetectedConnection


@dataclass(frozen=True)
class DiagramAnalysisResult:
    """Result of analyzing a diagram containing detected components and connections.
    
    Attributes:
        diagram_upload_id: UUID of the diagram that was analyzed
        components: Tuple of detected components in the diagram
        connections: Tuple of detected connections between components
    """
    
    diagram_upload_id: UUID
    components: tuple[DetectedComponent, ...] = field(default_factory=tuple)
    connections: tuple[DetectedConnection, ...] = field(default_factory=tuple)
    
    def __post_init__(self) -> None:
        """Validate the analysis result attributes."""
        if not isinstance(self.diagram_upload_id, UUID):
            raise TypeError("diagram_upload_id must be a UUID")
        
        if not isinstance(self.components, tuple):
            raise TypeError("components must be a tuple")
        
        for component in self.components:
            if not isinstance(component, DetectedComponent):
                raise TypeError("all components must be DetectedComponent instances")
        
        if not isinstance(self.connections, tuple):
            raise TypeError("connections must be a tuple")
        
        for connection in self.connections:
            if not isinstance(connection, DetectedConnection):
                raise TypeError("all connections must be DetectedConnection instances")
    
    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"DiagramAnalysisResult(diagram_upload_id={self.diagram_upload_id!s}, "
            f"component_count={len(self.components)}, "
            f"connection_count={len(self.connections)})"
        )
    
    @property
    def component_count(self) -> int:
        """Return the number of detected components."""
        return len(self.components)
    
    @property
    def connection_count(self) -> int:
        """Return the number of detected connections."""
        return len(self.connections)
