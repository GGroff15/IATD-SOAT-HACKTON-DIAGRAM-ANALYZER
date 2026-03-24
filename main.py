import os

import boto3
import structlog
import uvicorn

from app.adapter.driver.api.processing_start_endpoint import create_app
from app.infrastructure.logging.config import configure_logging
from app.infrastructure.config.settings import Settings
from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.adapter.driven.conversion.pdf2image_converter import Pdf2ImageConverter
from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.adapter.driven.detection.opencv_connection_detector import OpenCVConnectionDetector
from app.adapter.driven.ocr.textract_ocr import TextractOCR
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.application.services.graph_builder_service import GraphBuilderService


def main() -> None:
    """Composition root: wire all dependencies together."""
    configure_logging()
    logger = structlog.get_logger()
    
    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception:
        print("Missing required configuration. Ensure S3_BUCKET_NAME is set in the environment or .env file.")
        raise

    # Create infrastructure clients
    client_kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
        # For LocalStack/local testing, provide dummy credentials if not present
        if not os.environ.get("AWS_ACCESS_KEY_ID"):
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"
    
    s3_client = boto3.client("s3", **client_kwargs)
    textract_client = boto3.client("textract", **client_kwargs)

    # Create driven adapters (outbound ports)
    file_storage = S3FileStorage(s3_client=s3_client, bucket_name=settings.S3_BUCKET_NAME)
    image_converter = Pdf2ImageConverter()
    diagram_detector = YoloDetector(
        model_name=settings.YOLO_MODEL_NAME,
        confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
        device=settings.YOLO_DEVICE,
    )
    connection_detector = OpenCVConnectionDetector()
    text_extractor = TextractOCR(textract_client=textract_client)
    graph_builder = GraphBuilderService()

    # Create application service with injected dependencies
    processor = DiagramUploadProcessor(
        file_storage=file_storage,
        image_converter=image_converter,
        diagram_detector=diagram_detector,
        connection_detector=connection_detector,
        text_extractor=text_extractor,
        graph_builder=graph_builder,
    )

    app = create_app(processor=processor.process)

    logger.info("starting.diagram-analyzer-service")
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)


if __name__ == "__main__":
    main()
