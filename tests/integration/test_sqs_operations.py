def test_sqs_send_receive(sqs_client):
    q = sqs_client.create_queue(QueueName="test-queue")
    url = q["QueueUrl"]
    sqs_client.send_message(QueueUrl=url, MessageBody="hello")
    res = sqs_client.receive_message(QueueUrl=url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
    msgs = res.get("Messages", [])
    assert len(msgs) == 1
    assert msgs[0]["Body"] == "hello"
    sqs_client.delete_message(QueueUrl=url, ReceiptHandle=msgs[0]["ReceiptHandle"])