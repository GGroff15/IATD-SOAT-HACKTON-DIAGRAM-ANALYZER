from testcontainers.localstack import LocalStackContainer


def before_all(context):
    context.localstack = LocalStackContainer().with_services("s3", "sqs")
    context.localstack.start()


def after_all(context):
    try:
        context.localstack.stop()
    except Exception:
        pass


def before_scenario(context, scenario):
    context.s3 = context.localstack.get_client("s3")
    context.sqs = context.localstack.get_client("sqs")


def after_scenario(context, scenario):
    # cleanup S3 buckets
    try:
        for b in context.s3.list_buckets().get("Buckets", []) or []:
            name = b["Name"]
            for obj in context.s3.list_objects_v2(Bucket=name).get("Contents", []) or []:
                context.s3.delete_object(Bucket=name, Key=obj["Key"])
            context.s3.delete_bucket(Bucket=name)
    except Exception:
        pass
    # cleanup SQS queues
    try:
        for url in context.sqs.list_queues().get("QueueUrls", []) or []:
            context.sqs.delete_queue(QueueUrl=url)
    except Exception:
        pass
