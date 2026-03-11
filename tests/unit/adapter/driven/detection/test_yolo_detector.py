from io import BytesIO
from uuid import uuid4
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
import numpy as np
from PIL import Image

from app.core.application.exceptions import DiagramDetectionError
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


@pytest.fixture
def sample_image_bytes():
    """Generate sample PNG image bytes for testing"""
    img = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_yolo_model():
    """Create a mock YOLO model for testing"""
    mock_model = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)
    return mock_model


def test_yolo_detector_initialization_success(mock_yolo_model):
    """Test that YoloDetector initializes successfully with valid parameters."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    # Act
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(
            model_name="yolov8n.pt",
            confidence_threshold=0.5,
            device="cpu",
        )
    
    # Assert
    assert detector.model_name == "yolov8n.pt"
    assert detector.confidence_threshold == 0.5
    assert detector.device == "cpu"
    mock_yolo_model.to.assert_called_once_with("cpu")


def test_yolo_detector_initialization_failure_raises_error():
    """Test that YoloDetector initialization failure raises DiagramDetectionError."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    # Act & Assert
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", side_effect=Exception("Model load failed")):
        with pytest.raises(DiagramDetectionError, match="Failed to initialize YOLO model"):
            YoloDetector(model_name="invalid_model.pt")


def test_yolo_detector_detect_single_object(mock_yolo_model, sample_image_bytes):
    """Test detection of a single object returns correct DiagramAnalysisResult."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    
    # Mock YOLO result with single detection
    mock_boxes = MagicMock()
    mock_boxes.xyxy = [np.array([100.0, 150.0, 200.0, 250.0])]  # [x1, y1, x2, y2]
    mock_boxes.conf = [np.array(0.85)]
    mock_boxes.cls = [np.array(0)]  # class_id = 0
    
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes
    mock_result.names = {0: "person"}
    
    mock_yolo_model.return_value = [mock_result]
    
    # Act
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(model_name="yolov8n.pt", confidence_threshold=0.5)
        result = detector.detect(diagram_id, sample_image_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id
    assert result.component_count == 1
    
    component = result.components[0]
    assert component.class_name == "person"
    assert component.confidence == 0.85
    assert component.x == 100.0
    assert component.y == 150.0
    assert component.width == 100.0  # 200 - 100
    assert component.height == 100.0  # 250 - 150
    
    # Verify YOLO model was called with correct parameters
    mock_yolo_model.assert_called_once()
    call_args = mock_yolo_model.call_args
    assert call_args[1]["conf"] == 0.5
    assert call_args[1]["verbose"] is False


def test_yolo_detector_detect_multiple_objects(mock_yolo_model, sample_image_bytes):
    """Test detection of multiple objects returns all detected components."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    
    # Mock YOLO result with multiple detections
    mock_boxes = MagicMock()
    mock_boxes.xyxy = [
        np.array([10.0, 20.0, 50.0, 80.0]),   # person
        np.array([100.0, 120.0, 200.0, 220.0]),  # car
        np.array([300.0, 350.0, 400.0, 450.0]),  # dog
    ]
    mock_boxes.conf = [np.array(0.92), np.array(0.78), np.array(0.65)]
    mock_boxes.cls = [np.array(0), np.array(2), np.array(16)]
    
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes
    mock_result.names = {0: "person", 2: "car", 16: "dog"}
    
    mock_yolo_model.return_value = [mock_result]
    
    # Act
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(model_name="yolov8n.pt")
        result = detector.detect(diagram_id, sample_image_bytes)
    
    # Assert
    assert result.component_count == 3
    
    # Check first component (person)
    assert result.components[0].class_name == "person"
    assert result.components[0].confidence == 0.92
    assert result.components[0].x == 10.0
    assert result.components[0].width == 40.0
    
    # Check second component (car)
    assert result.components[1].class_name == "car"
    assert result.components[1].confidence == 0.78
    
    # Check third component (dog)
    assert result.components[2].class_name == "dog"
    assert result.components[2].confidence == 0.65


def test_yolo_detector_detect_no_objects(mock_yolo_model, sample_image_bytes):
    """Test detection with no objects returns empty components list."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    
    # Mock YOLO result with no detections
    mock_boxes = MagicMock()
    mock_boxes.xyxy = []
    mock_boxes.conf = []
    mock_boxes.cls = []
    
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes
    mock_result.names = {}
    
    # Make len(boxes) return 0
    type(mock_boxes).__len__ = lambda x: 0
    
    mock_yolo_model.return_value = [mock_result]
    
    # Act
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(model_name="yolov8n.pt")
        result = detector.detect(diagram_id, sample_image_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id
    assert result.component_count == 0
    assert result.components == tuple()


def test_yolo_detector_detect_invalid_image_raises_error(mock_yolo_model):
    """Test detection with invalid image data raises DiagramDetectionError."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    invalid_image_bytes = b"not an image"
    
    # Act & Assert
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(model_name="yolov8n.pt")
        with pytest.raises(DiagramDetectionError, match="Failed to detect components"):
            detector.detect(diagram_id, invalid_image_bytes)


def test_yolo_detector_detect_inference_failure_raises_error(mock_yolo_model, sample_image_bytes):
    """Test that YOLO inference failure raises DiagramDetectionError."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    mock_yolo_model.side_effect = RuntimeError("CUDA out of memory")
    
    # Act & Assert
    with patch("app.adapter.driven.detection.yolo_detector.YOLO") as mock_yolo_class:
        mock_instance = MagicMock()
        mock_instance.to = MagicMock(return_value=mock_instance)
        mock_instance.side_effect = RuntimeError("CUDA out of memory")
        mock_yolo_class.return_value = mock_instance
        
        detector = YoloDetector(model_name="yolov8n.pt")
        with pytest.raises(DiagramDetectionError, match="Failed to detect components"):
            detector.detect(diagram_id, sample_image_bytes)


def test_yolo_detector_custom_confidence_threshold(mock_yolo_model, sample_image_bytes):
    """Test that custom confidence threshold is used in detection."""
    # Arrange
    from app.adapter.driven.detection.yolo_detector import YoloDetector
    
    diagram_id = uuid4()
    custom_threshold = 0.75
    
    # Mock empty result
    mock_boxes = MagicMock()
    mock_boxes.xyxy = []
    type(mock_boxes).__len__ = lambda x: 0
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes
    mock_yolo_model.return_value = [mock_result]
    
    # Act
    with patch("app.adapter.driven.detection.yolo_detector.YOLO", return_value=mock_yolo_model):
        detector = YoloDetector(
            model_name="yolov8n.pt",
            confidence_threshold=custom_threshold,
        )
        detector.detect(diagram_id, sample_image_bytes)
    
    # Assert - verify confidence threshold was passed to YOLO
    call_args = mock_yolo_model.call_args
    assert call_args[1]["conf"] == custom_threshold
