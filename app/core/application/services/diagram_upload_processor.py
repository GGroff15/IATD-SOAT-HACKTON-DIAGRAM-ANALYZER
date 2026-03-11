import structlog

from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.application.ports.file_storage import FileStorage
from app.core.application.ports.image_converter import ImageConverter

logger = structlog.get_logger()


class DiagramUploadProcessor:
    """Application service for processing diagram upload events."""

    def __init__(self, file_storage: FileStorage, image_converter: ImageConverter):
        """Initialize the processor with injected dependencies.

        Args:
            file_storage: File storage adapter for downloading diagram files
            image_converter: Image converter adapter for normalizing file formats
        """
        self.file_storage = file_storage
        self.image_converter = image_converter

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
        
        # Future: Add diagram analysis logic here
        # For now, the normalized image is ready for analysis
