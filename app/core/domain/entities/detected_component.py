from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedComponent:
    """Represents a component detected in a diagram with bounding box and classification.
    
    Attributes:
        class_name: The detected object class/category name
        confidence: Detection confidence score (0.0 to 1.0)
        x: Bounding box top-left x-coordinate (pixels)
        y: Bounding box top-left y-coordinate (pixels)
        width: Bounding box width (pixels)
        height: Bounding box height (pixels)
    """
    
    class_name: str
    confidence: float
    x: float
    y: float
    width: float
    height: float
    
    def __post_init__(self) -> None:
        """Validate the detected component attributes."""
        if not self.class_name or not str(self.class_name).strip():
            raise ValueError("class_name must be a non-empty string")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        
        if self.width < 0:
            raise ValueError("width must be non-negative")
        
        if self.height < 0:
            raise ValueError("height must be non-negative")
    
    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"DetectedComponent(class_name={self.class_name!r}, "
            f"confidence={self.confidence:.2f}, "
            f"bbox=({self.x:.1f}, {self.y:.1f}, {self.width:.1f}, {self.height:.1f}))"
        )
