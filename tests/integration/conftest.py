import pytest
from testcontainers.localstack import LocalStackContainer


@pytest.fixture(scope="session")
def localstack_container():
    """Session-scoped LocalStack container for integration tests"""
    container = (
        LocalStackContainer(image="localstack/localstack:latest")
        .with_services("s3")
    )
    container.start()
    yield container
    container.stop()


@pytest.fixture
def s3_client(localstack_container):
    s3 = localstack_container.get_client("s3")
    yield s3
    # cleanup buckets
    try:
        for b in s3.list_buckets().get("Buckets", []):
            name = b["Name"]
            for obj in s3.list_objects_v2(Bucket=name).get("Contents", []) or []:
                s3.delete_object(Bucket=name, Key=obj["Key"])
            s3.delete_bucket(Bucket=name)
    except Exception:
        pass
