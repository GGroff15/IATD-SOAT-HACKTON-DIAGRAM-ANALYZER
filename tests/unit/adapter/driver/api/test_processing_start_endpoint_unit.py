from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.adapter.driver.api.processing_start_endpoint import create_app


def test_processing_start_returns_acknowledgment_with_protocol() -> None:
    processor = AsyncMock()
    client = TestClient(create_app(processor=processor))

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
    client = TestClient(create_app(processor=processor))

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
    client = TestClient(create_app(processor=processor))

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
    processor.assert_not_awaited()
