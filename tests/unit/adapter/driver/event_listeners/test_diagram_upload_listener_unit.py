import json
from uuid import uuid4

from app.adapter.driver.event_listeners.diagram_upload_listener import DiagramUploadListener
from app.core.domain.entities.diagram_upload import DiagramUpload


class DummyClient:
    def __init__(self):
        self.deleted = None

    def delete_message(self, QueueUrl, ReceiptHandle):
        self.deleted = {"QueueUrl": QueueUrl, "ReceiptHandle": ReceiptHandle}


async def dummy_processor(upload: DiagramUpload) -> None:
    """Mock processor for testing."""
    pass


def test_handle_message_parses_and_deletes():
    queue_url = "https://example"
    dummy_client = DummyClient()
    
    # Inject dependencies
    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=dummy_client,
        processor=dummy_processor,
    )

    body = {"diagramUploadId": str(uuid4()), "folder": "test-folder"}
    message = {"Body": json.dumps(body), "ReceiptHandle": "rh-1", "MessageId": "m-1"}
    listener.handle_message(message)

    assert dummy_client.deleted is not None
    assert dummy_client.deleted["QueueUrl"] == queue_url
