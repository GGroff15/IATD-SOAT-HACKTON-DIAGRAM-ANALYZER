import json
import threading
import time
from unittest.mock import AsyncMock
from uuid import uuid4

from app.adapter.driver.event_listeners.diagram_upload_listener import DiagramUploadListener


def test_diagram_upload_listener_integration(sqs_client):
    q = sqs_client.create_queue(QueueName="test-diagram-queue")
    queue_url = q["QueueUrl"]

    # Mock the async processor to isolate listener behavior
    mock_processor = AsyncMock()

    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=sqs_client,
        processor=mock_processor,
    )

    t = threading.Thread(target=listener.start, daemon=True)
    t.start()

    try:
        diagram_upload_id = str(uuid4())
        body = {"diagramUploadId": diagram_upload_id, "folder": "integration-folder"}
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))

        time.sleep(3)

        # Verify message was consumed from queue
        attrs = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]) 
        approx = int(attrs.get("Attributes", {}).get("ApproximateNumberOfMessages", 0))
        assert approx == 0
        
        # Verify processor was called with the DiagramUpload entity
        mock_processor.assert_called_once()
        upload_entity = mock_processor.call_args[0][0]
        assert str(upload_entity.diagram_upload_id) == diagram_upload_id
        assert upload_entity.folder == "integration-folder"
    finally:
        listener.stop()
        t.join(timeout=5)
