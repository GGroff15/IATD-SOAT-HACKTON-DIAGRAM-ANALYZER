import asyncio
import threading
import time
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.adapter.driver.api.processing_start_endpoint import create_app


def _wait_for(condition, timeout: float = 1.0, interval: float = 0.01) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()


def test_processing_start_returns_acknowledgment_with_protocol() -> None:
    processed = threading.Event()

    async def processor(_upload) -> None:
        processed.set()

    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "https://example.com/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "protocol": "550e8400-e29b-41d4-a716-446655440000",
    }
    assert processed.wait(timeout=1.0)


def test_processing_start_returns_accepted_immediately_while_processing_runs_async() -> None:
    started = threading.Event()

    async def processor(_upload) -> None:
        started.set()
        await asyncio.sleep(0.6)

    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    start = time.perf_counter()
    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440001",
            "file": {
                "url": "https://example.com/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 202
    assert elapsed < 0.45
    assert started.wait(timeout=1.0)


def test_processing_start_rejects_missing_required_field() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "https://example.com/uploads/project-a/diagram.pdf",
            },
        },
    )

    assert response.status_code == 422
    processor.assert_not_awaited()


def test_processing_start_rejects_non_http_url() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "s3://example-bucket/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 422
    assert "http" in response.json()["detail"].lower()
    processor.assert_not_awaited()


def test_processing_start_accepts_root_object_key_without_folder_extraction() -> None:
    processed = threading.Event()
    captured: dict[str, object] = {}

    async def processor(upload) -> None:
        captured["upload"] = upload
        processed.set()

    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440002",
            "file": {
                "url": "https://example.com/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    assert processed.wait(timeout=1.0)
    upload = captured["upload"]
    assert upload.file_url == "https://example.com/diagram.pdf"
    assert upload.diagram_upload_id == UUID("550e8400-e29b-41d4-a716-446655440002")


def test_processing_start_reports_background_processing_failure() -> None:
    failed = threading.Event()

    async def processor(_upload) -> None:
        failed.set()
        raise RuntimeError("database password=secret")

    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "https://example.com/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    assert failed.wait(timeout=1.0)
    assert _wait_for(lambda: reporter.publish_error.await_count == 1)
    report = reporter.publish_error.await_args.args[0]
    assert report.reason == "An unexpected error occurred."
    assert "password" not in report.reason


def test_processing_start_returns_response_when_error_report_publication_fails() -> None:
    failed = threading.Event()

    async def processor(_upload) -> None:
        failed.set()
        raise RuntimeError("internal failure")

    reporter = AsyncMock()
    reporter.publish_error = AsyncMock(side_effect=RuntimeError("queue unavailable"))
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440003",
            "file": {
                "url": "https://example.com/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    assert failed.wait(timeout=1.0)
    assert _wait_for(lambda: reporter.publish_error.await_count == 1)
