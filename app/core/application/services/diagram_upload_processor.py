import structlog
from app.core.domain.entities.diagram_upload import DiagramUpload

logger = structlog.get_logger()


async def process_diagram_upload(upload: DiagramUpload) -> None:
    """Placeholder processing for a diagram upload event.

    Currently this just logs receipt; real analysis will be implemented later.
    """
    logger.info(
        "diagram_upload.process.received",
        diagram_upload_id=str(upload.diagram_upload_id),
        folder=upload.folder,
    )
