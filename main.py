import boto3
import structlog
import uvicorn
from paddleocr import PaddleOCR

from app.adapter.driver.api.processing_start_endpoint import create_app
from app.adapter.driven.event_publishers.noop_error_report_publisher import NoOpErrorReportPublisher
from app.adapter.driven.event_publishers.noop_graph_result_publisher import NoOpGraphResultPublisher
from app.infrastructure.logging.config import configure_logging
from app.infrastructure.config.settings import Settings
from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.adapter.driven.conversion.pdf2image_converter import Pdf2ImageConverter
from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector
from app.adapter.driven.ocr.paddle_ocr import PaddleOCRExtractor
from app.core.application.services.architectural_rules_validator_service import (
    ArchitecturalRulesValidatorService,
)
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.application.services.graph_builder_service import GraphBuilderService


def _build_paddle_ocr_engine(settings: Settings):
    """Build PaddleOCR engine with backward-compatible constructor args."""
    logger = structlog.get_logger()

    normalized_device = settings.PADDLE_OCR_DEVICE.strip().lower()
    if normalized_device == "gpu":
        normalized_device = "gpu:0"

    engine_kwargs = {"lang": settings.PADDLE_OCR_LANG}

    if settings.PADDLE_OCR_MODEL_DIR:
        engine_kwargs["model_dir"] = settings.PADDLE_OCR_MODEL_DIR

    # Keep OCR pipeline minimal for diagram snippets and avoid optional doc modules
    # that can trigger unstable runtime paths on some CPU backends.
    lean_pipeline_kwargs = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }

    runtime_compat_kwargs = {
        "enable_mkldnn": settings.PADDLE_OCR_ENABLE_MKLDNN,
    }

    constructor_attempts = [
        {
            "device": normalized_device,
            **lean_pipeline_kwargs,
            **runtime_compat_kwargs,
            **engine_kwargs,
        },
        {
            "device": normalized_device,
            **lean_pipeline_kwargs,
            **runtime_compat_kwargs,
            **engine_kwargs,
        },
        {
            "device": normalized_device,
            **runtime_compat_kwargs,
            "use_angle_cls": settings.PADDLE_OCR_USE_ANGLE_CLS,
            **engine_kwargs,
        },
        {
            "device": normalized_device,
            **runtime_compat_kwargs,
            **engine_kwargs,
        },
        {
            **runtime_compat_kwargs,
            "use_angle_cls": settings.PADDLE_OCR_USE_ANGLE_CLS,
            **engine_kwargs,
        },
        {**lean_pipeline_kwargs, **runtime_compat_kwargs, **engine_kwargs},
        {**lean_pipeline_kwargs, **engine_kwargs},
        {**runtime_compat_kwargs, **engine_kwargs},
        {"use_angle_cls": settings.PADDLE_OCR_USE_ANGLE_CLS, **engine_kwargs},
        engine_kwargs,
    ]

    last_error: Exception | None = None
    for kwargs in constructor_attempts:
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError) as error:
            last_error = error
            logger.warning(
                "paddle.ocr.init.retry",
                attempted_args=sorted(kwargs.keys()),
                error=str(error),
            )

    assert last_error is not None
    raise last_error


def build_application():
    """Composition root: wire all dependencies together and return the ASGI app."""
    configure_logging()

    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception:
        print("Missing required configuration. Ensure S3_BUCKET_NAME is set in the environment or .env file.")
        raise

    # Create infrastructure clients
    client_kwargs = {"region_name": settings.AWS_REGION}

    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_SESSION_TOKEN:
        client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

    if settings.AWS_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
        # For LocalStack/local testing, provide dummy credentials if not configured
        if "aws_access_key_id" not in client_kwargs:
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"
    
    s3_client = boto3.client("s3", **client_kwargs)

    # Create driven adapters (outbound ports)
    file_storage = S3FileStorage(s3_client=s3_client, bucket_name=settings.S3_BUCKET_NAME)
    error_report_publisher = NoOpErrorReportPublisher()
    graph_result_publisher = NoOpGraphResultPublisher()
    image_converter = Pdf2ImageConverter()
    component_detector = YoloDetector(
        model_name=settings.YOLO_MODEL_NAME,
        confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
        device=settings.YOLO_DEVICE,
        excluded_class_names=(
            settings.YOLO_CONNECTION_ARROW_LINE_CLASS,
            settings.YOLO_CONNECTION_ARROW_HEAD_CLASS,
        ),
    )
    connection_detector = YoloConnectionDetector(
        model_name=settings.YOLO_MODEL_NAME,
        confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
        device=settings.YOLO_DEVICE,
        arrow_line_class_name=settings.YOLO_CONNECTION_ARROW_LINE_CLASS,
        arrow_head_class_name=settings.YOLO_CONNECTION_ARROW_HEAD_CLASS,
    )
    paddle_ocr_engine = _build_paddle_ocr_engine(settings)
    text_extractor = PaddleOCRExtractor(
        ocr_engine=paddle_ocr_engine,
        use_angle_cls=settings.PADDLE_OCR_USE_ANGLE_CLS,
    )
    graph_builder = GraphBuilderService()
    architectural_rules_validator = ArchitecturalRulesValidatorService()

    # Create application service with injected dependencies
    processor = DiagramUploadProcessor(
        file_storage=file_storage,
        image_converter=image_converter,
        component_detector=component_detector,
        connection_detector=connection_detector,
        text_extractor=text_extractor,
        graph_builder=graph_builder,
        architectural_rules_validator=architectural_rules_validator,
        graph_result_publisher=graph_result_publisher,
    )

    return create_app(
        processor=processor.process,
        error_report_publisher=error_report_publisher,
    ), settings


app, _settings = build_application()


def main() -> None:
    """Run the API service using Uvicorn."""
    logger = structlog.get_logger()

    logger.info("starting.diagram-analyzer-service")
    uvicorn.run(app, host=_settings.API_HOST, port=_settings.API_PORT)


if __name__ == "__main__":
    main()
