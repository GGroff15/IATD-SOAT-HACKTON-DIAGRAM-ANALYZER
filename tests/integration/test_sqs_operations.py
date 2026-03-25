import pytest
from testcontainers.localstack import LocalStackContainer


@pytest.fixture(scope="session")
def localstack_sqs_container():
    container = LocalStackContainer(image="localstack/localstack:latest").with_services("sqs")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def sqs_client(localstack_sqs_container):
    sqs = localstack_sqs_container.get_client("sqs")
    yield sqs
    try:
        for url in sqs.list_queues().get("QueueUrls", []) or []:
            sqs.delete_queue(QueueUrl=url)
    except Exception:
        pass


def test_sqs_send_receive(sqs_client):
    q = sqs_client.create_queue(QueueName="test-queue")
    url = q["QueueUrl"]
    sqs_client.send_message(QueueUrl=url, MessageBody="hello")
    res = sqs_client.receive_message(QueueUrl=url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
    msgs = res.get("Messages", [])
    assert len(msgs) == 1
    assert msgs[0]["Body"] == "hello"
    sqs_client.delete_message(QueueUrl=url, ReceiptHandle=msgs[0]["ReceiptHandle"])