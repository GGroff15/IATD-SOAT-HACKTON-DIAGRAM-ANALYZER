import json
import asyncio
import structlog
from typing import Callable, Awaitable

from app.adapter.driver.event_listeners.sqs_listener import SQSListener
from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.application.exceptions import InvalidMessageError
from app.infrastructure.logging.correlation import set_correlation_id, clear_correlation_id

logger = structlog.get_logger()


class DiagramUploadListener(SQSListener):
    def __init__(self, queue_url: str, sqs_client, processor: Callable[[DiagramUpload], Awaitable[None]]):
        """Initialize diagram upload listener with injected dependencies.
        
        Args:
            queue_url: URL of the SQS queue to listen to
            sqs_client: Boto3 SQS client (injected dependency)
            processor: Async function to process diagram uploads (injected dependency)
        """
        super().__init__(queue_url, sqs_client)
        self.processor = processor

    def handle_message(self, message: dict) -> None:
        body = message.get("Body")
        if not body:
            raise InvalidMessageError("empty message body")
        try:
            payload = json.loads(body)
        except Exception as exc:
            raise InvalidMessageError("invalid JSON") from exc

        diagram_id = payload.get("diagramUploadId") or payload.get("diagram_upload_id")
        folder = payload.get("folder")
        if not diagram_id:
            raise InvalidMessageError("missing diagramUploadId")

        upload = DiagramUpload(diagram_id, folder)
        set_correlation_id(str(upload.diagram_upload_id))
        try:
            asyncio.run(self.processor(upload))
            # delete message after successful processing
            self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=message["ReceiptHandle"])
            logger.info("sqs.diagram_upload.processed", message_id=message.get("MessageId"), diagram_upload_id=str(upload.diagram_upload_id))
        except Exception:
            logger.exception("sqs.diagram_upload.processing_error", message_id=message.get("MessageId"))
            raise
        finally:
            clear_correlation_id()
