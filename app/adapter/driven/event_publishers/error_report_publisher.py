import structlog
import pika

from app.core.application.ports.error_report_payload import ErrorReportPayload
from app.core.application.ports.error_report_publisher import ErrorReportPublisher

logger = structlog.get_logger()


class RabbitMqErrorReportPublisher(ErrorReportPublisher):
    
    def __init__(self, rabbitmq_host: str = "localhost", rabbitmq_port: int = 5672, rabbitmq_queue_name: str = "analisys_response"):
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_queue_name = rabbitmq_queue_name

    async def publish_error(self, payload: ErrorReportPayload) -> None:
        logger.info(
            "error_report.noop_published",
            classification=payload.classification,
            path=payload.path,
            timestamp=payload.timestamp,
        )

        connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_host, self.rabbitmq_port))
        channel = connection.channel()
        channel.queue_declare(queue=self.rabbitmq_queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=self.rabbitmq_queue_name,
            body=str(
                {
                    "protocol": str(payload.correlation_id),
                    "status": "error",
                    "reason": payload.reason,
                }
            ),
        )
