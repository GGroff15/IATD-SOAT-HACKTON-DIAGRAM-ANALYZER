from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.adapter.driver.api.processing_start_endpoint import create_app


def test_processing_start_returns_acknowledgment_with_protocol() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "protocol": "550e8400-e29b-41d4-a716-446655440000",
    }
    processor.assert_awaited_once()


def test_processing_start_rejects_missing_required_field() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
            },
        },
    )

    assert response.status_code == 422
    processor.assert_not_awaited()


def test_processing_start_rejects_non_s3_url() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "https://example.com/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 422
    assert "s3://" in response.json()["detail"]
    processor.assert_not_awaited()


def test_processing_start_accepts_root_object_key_without_folder_extraction() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440002",
            "file": {
                "url": "s3://input-bucket/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    processor.assert_awaited_once()
    upload = processor.await_args.args[0]
    assert upload.file_url == "s3://input-bucket/diagram.pdf"
    assert upload.diagram_upload_id == UUID("550e8400-e29b-41d4-a716-446655440002")


def test_processing_start_returns_problem_details_for_unhandled_exception() -> None:
    processor = AsyncMock(side_effect=RuntimeError("database password=secret"))
    reporter = AsyncMock()
    client = TestClient(
        create_app(processor=processor, error_report_publisher=reporter),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440000",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "urn:diagram-analyzer:error:internal",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "/processing-start",
    }

    reporter.publish_error.assert_awaited_once()
    report = reporter.publish_error.await_args.args[0]
    assert report.reason == "An unexpected error occurred."
    assert "password" not in report.reason


def test_processing_start_returns_response_when_error_report_publication_fails() -> None:
    processor = AsyncMock(side_effect=RuntimeError("internal failure"))
    reporter = AsyncMock()
    reporter.publish_error = AsyncMock(side_effect=RuntimeError("queue unavailable"))
    client = TestClient(
        create_app(processor=processor, error_report_publisher=reporter),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440003",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 500
    assert response.json()["type"] == "urn:diagram-analyzer:error:internal"
    reporter.publish_error.assert_awaited_once()
