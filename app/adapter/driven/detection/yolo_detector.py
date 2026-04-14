from io import BytesIO
from uuid import UUID

import structlog
from PIL import Image
from ultralytics import YOLO

from app.core.application.exceptions import DiagramDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult

logger = structlog.get_logger()


class YoloDetector:
    """Adapter for detecting diagram components using YOLO object detection."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
        excluded_class_names: tuple[str, ...] = ("arrow_line", "arrow_head"),
    ):
        """Initialize the YOLO detector.

        Args:
            model_name: YOLO model to use (e.g., 'yolov8n.pt', 'yolov8s.pt')
            confidence_threshold: Minimum confidence score for detections (0.0 to 1.0)
            device: Device to run inference on ('cpu' or 'cuda')
            excluded_class_names: Class labels excluded from component output
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.excluded_class_names = set(excluded_class_names)
        
        logger.info(
            "yolo_detector.initializing",
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            device=device,
            excluded_class_names=sorted(self.excluded_class_names),
        )
        
        try:
            self.model = YOLO(model_name)
            self.model.to(device)
            logger.info("yolo_detector.initialized", model_name=model_name)
        except Exception as exc:
            logger.error(
                "yolo_detector.initialization_failed",
                model_name=model_name,
                error=str(exc),
                exc_info=True,
            )
            raise DiagramDetectionError(
                f"Failed to initialize YOLO model '{model_name}': {exc}"
            ) from exc

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
        logger.info(
            "diagram_detection.started",
            diagram_upload_id=str(diagram_upload_id),
            image_size_bytes=len(image_bytes),
        )
        
        try:
            # Load image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Run YOLO inference
            results = self.model(image, conf=self.confidence_threshold, verbose=False)
            
            # Extract detections from results
            components = []
            excluded_count = 0
            for result in results:
                boxes = result.boxes
                for i in range(len(boxes)):
                    box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                    confidence = float(boxes.conf[i].cpu().numpy())
                    class_id = int(boxes.cls[i].cpu().numpy())
                    class_name = result.names[class_id]

                    if class_name in self.excluded_class_names:
                        excluded_count += 1
                        continue
                    
                    # Convert from [x1, y1, x2, y2] to [x, y, width, height]
                    x1, y1, x2, y2 = box
                    x = float(x1)
                    y = float(y1)
                    width = float(x2 - x1)
                    height = float(y2 - y1)
                    
                    component = DetectedComponent(
                        class_name=class_name,
                        confidence=confidence,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                    )
                    components.append(component)
            
            result = DiagramAnalysisResult(
                diagram_upload_id=diagram_upload_id,
                components=tuple(components),
            )
            
            logger.info(
                "diagram_detection.completed",
                diagram_upload_id=str(diagram_upload_id),
                component_count=len(components),
                excluded_detection_count=excluded_count,
                components=[
                    {
                        "class_name": c.class_name,
                        "confidence": round(c.confidence, 3),
                        "bbox": {
                            "x": round(c.x, 1),
                            "y": round(c.y, 1),
                            "width": round(c.width, 1),
                            "height": round(c.height, 1),
                        },
                    }
                    for c in components
                ],
            )
            
            return result
            
        except DiagramDetectionError:
            raise
        except Exception as exc:
            logger.error(
                "diagram_detection.failed",
                diagram_upload_id=str(diagram_upload_id),
                error=str(exc),
                exc_info=True,
            )
            raise DiagramDetectionError(
                f"Failed to detect components in diagram: {exc}"
            ) from exc
