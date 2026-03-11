import threading
import signal
import time
import logging

logger = logging.getLogger(__name__)


class SQSListener:
    def __init__(self, queue_url: str, sqs_client):
        """Initialize SQS listener with injected dependencies.
        
        Args:
            queue_url: URL of the SQS queue to listen to
            sqs_client: Boto3 SQS client (injected dependency)
        """
        self.queue_url = queue_url
        self.client = sqs_client
        self._stop_event = threading.Event()

    def start(self) -> None:
        logger.info("sqs.listener.starting", extra={"queue_url": self.queue_url})
        self._register_signals()
        try:
            self._run_loop()
        finally:
            logger.info("sqs.listener.stopped")

    def stop(self) -> None:
        self._stop_event.set()

    def _register_signals(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, lambda *_: self.stop())
            except Exception:
                # Not all platforms allow signal registration (e.g., Windows threads)
                pass

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                resp = self.client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    MessageAttributeNames=["All"],
                    AttributeNames=["All"],
                )
                messages = resp.get("Messages", [])
                for msg in messages:
                    try:
                        self.handle_message(msg)
                    except Exception:
                        logger.exception("sqs.listener.message.failed", extra={"message_id": msg.get("MessageId")})
            except Exception:
                logger.exception("sqs.listener.receive_failed")
                time.sleep(1)
            time.sleep(0.1)

    def handle_message(self, message: dict) -> None:
        raise NotImplementedError()
