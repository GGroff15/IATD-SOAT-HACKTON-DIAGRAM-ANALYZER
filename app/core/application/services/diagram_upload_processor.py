import structlog

from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.application.ports.file_storage import FileStorage
from app.core.application.ports.image_converter import ImageConverter
from app.core.application.ports.diagram_detector import DiagramDetector
from app.core.application.ports.text_extractor import TextExtractor
from app.core.application.exceptions import TextExtractionError

logger = structlog.get_logger()


class DiagramUploadProcessor:
    """Application service for processing diagram upload events."""

    def __init__(
        self,
        file_storage: FileStorage,
        image_converter: ImageConverter,
        diagram_detector: DiagramDetector,
        text_extractor: TextExtractor,
    ):
        """Initialize the processor with injected dependencies.

        Args:
            file_storage: File storage adapter for downloading diagram files
            image_converter: Image converter adapter for normalizing file formats
            diagram_detector: Diagram detector adapter for identifying components
            text_extractor: Text extractor adapter for extracting text via OCR
        """
        self.file_storage = file_storage
        self.image_converter = image_converter
        self.diagram_detector = diagram_detector
        self.text_extractor = text_extractor

    async def process(self, upload: DiagramUpload) -> None:
        """Process a diagram upload event by downloading and analyzing the diagram.

        Args:
            upload: The diagram upload entity with metadata
        """
        logger.info(
            "diagram_upload.process.received",
            diagram_upload_id=str(upload.diagram_upload_id),
            folder=upload.folder,
            extension=upload.extension,
        )
        
        # Download the diagram file from storage
        file_content = await self.file_storage.download_file(
            folder=upload.folder,
            filename=str(upload.diagram_upload_id),
            extension=upload.extension,
        )
        
        logger.info(
            "diagram_upload.process.downloaded",
            diagram_upload_id=str(upload.diagram_upload_id),
            size_bytes=len(file_content),
        )
        
        # Convert file to normalized PNG format
        image_bytes = self.image_converter.convert_to_image(
            file_content=file_content,
            extension=upload.extension,
        )
        
        logger.info(
            "diagram_upload.process.converted",
            diagram_upload_id=str(upload.diagram_upload_id),
            image_size_bytes=len(image_bytes),
        )
        
        # Detect components in the diagram
        analysis_result = self.diagram_detector.detect(
            diagram_upload_id=upload.diagram_upload_id,
            image_bytes=image_bytes,
        )
        
        logger.info(
            "diagram_upload.process.detected",
            diagram_upload_id=str(upload.diagram_upload_id),
            component_count=analysis_result.component_count,
        )
        
        # Extract text from each detected component
        enriched_components = []
        for component in analysis_result.components:
            extracted_text = None
            try:
                extracted_text = self.text_extractor.extract_text(
                    image_bytes=image_bytes,
                    x=component.x,
                    y=component.y,
                    width=component.width,
                    height=component.height,
                )
                logger.debug(
                    "diagram_upload.process.text_extracted",
                    diagram_upload_id=str(upload.diagram_upload_id),
                    class_name=component.class_name,
                    text_length=len(extracted_text),
                )
            except TextExtractionError as e:
                logger.warning(
                    "diagram_upload.process.text_extraction_failed",
                    diagram_upload_id=str(upload.diagram_upload_id),
                    class_name=component.class_name,
                    error=str(e),
                )
                # Continue processing with None for extracted_text
            
            # Create enriched component with extracted text
            enriched_component = DetectedComponent(
                class_name=component.class_name,
                confidence=component.confidence,
                x=component.x,
                y=component.y,
                width=component.width,
                height=component.height,
                extracted_text=extracted_text if extracted_text else None,
            )
            enriched_components.append(enriched_component)
        
        logger.info(
            "diagram_upload.process.completed",
            diagram_upload_id=str(upload.diagram_upload_id),
            component_count=len(enriched_components),
            components_with_text=sum(1 for c in enriched_components if c.extracted_text),
        )
