import json
from uuid import uuid4

from app.adapter.driver.event_listeners.diagram_upload_listener import DiagramUploadListener
from app.core.domain.entities.diagram_upload import DiagramUpload


class DummyClient:
    def __init__(self):
        self.deleted = None

    def delete_message(self, QueueUrl, ReceiptHandle):
        self.deleted = {"QueueUrl": QueueUrl, "ReceiptHandle": ReceiptHandle}


class CaptureProcessor:
    """Processor that captures the upload for assertions."""
    def __init__(self):
        self.captured_upload = None
    
    async def __call__(self, upload: DiagramUpload) -> None:
        self.captured_upload = upload


def test_handle_message_parses_and_deletes():
    queue_url = "https://example"
    dummy_client = DummyClient()
    processor = CaptureProcessor()
    
    # Inject dependencies
    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=dummy_client,
        processor=processor,
    )

    body = {"diagramUploadId": str(uuid4()), "folder": "test-folder"}
    message = {"Body": json.dumps(body), "ReceiptHandle": "rh-1", "MessageId": "m-1"}
    listener.handle_message(message)

    assert dummy_client.deleted is not None
    assert dummy_client.deleted["QueueUrl"] == queue_url


def test_handle_message_defaults_to_pdf_extension():
    """Test that extension defaults to .pdf when not provided"""
    queue_url = "https://example"
    dummy_client = DummyClient()
    processor = CaptureProcessor()
    
    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=dummy_client,
        processor=processor,
    )

    body = {"diagramUploadId": str(uuid4()), "folder": "test-folder"}
    message = {"Body": json.dumps(body), "ReceiptHandle": "rh-1", "MessageId": "m-1"}
    listener.handle_message(message)

    assert processor.captured_upload is not None
    assert processor.captured_upload.extension == ".pdf"


def test_handle_message_parses_custom_extension():
    """Test that custom extension is parsed from message"""
    queue_url = "https://example"
    dummy_client = DummyClient()
    processor = CaptureProcessor()
    
    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=dummy_client,
        processor=processor,
    )

    body = {
        "diagramUploadId": str(uuid4()),
        "folder": "test-folder",
        "extension": ".png"
    }
    message = {"Body": json.dumps(body), "ReceiptHandle": "rh-1", "MessageId": "m-1"}
    listener.handle_message(message)

    assert processor.captured_upload is not None
    assert processor.captured_upload.extension == ".png"
