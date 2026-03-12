import os
import boto3
import structlog

from app.infrastructure.logging.config import configure_logging
from app.infrastructure.config.settings import Settings
from app.adapter.driver.event_listeners.diagram_upload_listener import DiagramUploadListener
from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.adapter.driven.conversion.pdf2image_converter import Pdf2ImageConverter
from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.adapter.driven.ocr.textract_ocr import TextractOCR
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor


def main() -> None:
    """Composition root: wire all dependencies together."""
    configure_logging()
    logger = structlog.get_logger()
    
    try:
        settings = Settings()
    except Exception as exc:
        print("Missing required configuration. Ensure SQS_QUEUE_URL and S3_BUCKET_NAME are set in the environment or .env file.")
        raise

    # Create infrastructure clients
    client_kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
        # For LocalStack/local testing, provide dummy credentials if not present
        if not os.environ.get("AWS_ACCESS_KEY_ID"):
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"
    
    sqs_client = boto3.client("sqs", **client_kwargs)
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
    text_extractor = TextractOCR(textract_client=textract_client)

    # Create application service with injected dependencies
    processor = DiagramUploadProcessor(
        file_storage=file_storage,
        image_converter=image_converter,
        diagram_detector=diagram_detector,
        text_extractor=text_extractor,
    )

    # Create driver adapter with all dependencies injected
    logger.info("starting.diagram-analyzer-service")
    listener = DiagramUploadListener(
        queue_url=settings.SQS_QUEUE_URL,
        sqs_client=sqs_client,
        processor=processor.process,
    )

    try:
        listener.start()
    except KeyboardInterrupt:
        logger.info("shutdown.requested")
        listener.stop()


if __name__ == "__main__":
    main()
