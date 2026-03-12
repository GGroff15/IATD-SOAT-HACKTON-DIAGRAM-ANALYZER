from dataclasses import dataclass
from enum import Enum


class ConnectionType(Enum):
    """Types of connections that can be detected in diagrams."""
    
    STRAIGHT = "straight"
    DASHED = "dashed"
    CURVED = "curved"
    ARROW = "arrow"


@dataclass(frozen=True)
class DetectedConnection:
    """Represents a connection (line, arrow, etc.) detected between components in a diagram.
    
    Attributes:
        connection_type: Type of the detected connection (straight, dashed, curved, arrow)
        confidence: Detection confidence score (0.0 to 1.0)
        start_point: Starting point of the connection as (x, y) tuple in pixels
        end_point: Ending point of the connection as (x, y) tuple in pixels
        source_component_index: Optional index of the source component in the components list
        target_component_index: Optional index of the target component in the components list
    """
    
    connection_type: ConnectionType
    confidence: float
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    source_component_index: int | None = None
    target_component_index: int | None = None
    
    def __post_init__(self) -> None:
        """Validate the detected connection attributes."""
        if not isinstance(self.connection_type, ConnectionType):
            raise TypeError("connection_type must be a ConnectionType enum value")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        
        if not isinstance(self.start_point, tuple) or len(self.start_point) != 2:
            raise TypeError("start_point must be a tuple of two floats")
        
        if not isinstance(self.end_point, tuple) or len(self.end_point) != 2:
            raise TypeError("end_point must be a tuple of two floats")
        
        # Validate coordinates are non-negative
        if self.start_point[0] < 0 or self.start_point[1] < 0:
            raise ValueError("start_point coordinates must be non-negative")
        
        if self.end_point[0] < 0 or self.end_point[1] < 0:
            raise ValueError("end_point coordinates must be non-negative")
        
        # Validate component indices if provided
        if self.source_component_index is not None and self.source_component_index < 0:
            raise ValueError("source_component_index must be non-negative or None")
        
        if self.target_component_index is not None and self.target_component_index < 0:
            raise ValueError("target_component_index must be non-negative or None")
    
    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"DetectedConnection(type={self.connection_type.value}, "
            f"confidence={self.confidence:.2f}, "
            f"from={self.start_point}, to={self.end_point})"
        )
