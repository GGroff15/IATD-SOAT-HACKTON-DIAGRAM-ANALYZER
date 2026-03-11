import pytest

@pytest.fixture(scope="session")
def aws_region():
    return "us-east-1"

@pytest.fixture
def test_bucket():
    return "test-bucket"

@pytest.fixture
def test_queue():
    return "test-queue"
