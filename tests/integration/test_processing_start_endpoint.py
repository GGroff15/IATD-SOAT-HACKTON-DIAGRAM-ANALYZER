from unittest.mock import AsyncMock, Mock
from uuid import UUID

from fastapi.testclient import TestClient

from app.adapter.driver.api.processing_start_endpoint import create_app
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


class StubFileStorage:
    def __init__(self) -> None:
        self.download_file = AsyncMock(return_value=b"pdf-bytes")


class StubImageConverter:
    def __init__(self) -> None:
        self.convert_to_image = Mock(return_value=b"png-bytes")


class StubDiagramDetector:
    def __init__(self) -> None:
        self.detect = Mock(
            return_value=DiagramAnalysisResult(diagram_upload_id=UUID("550e8400-e29b-41d4-a716-446655440000"))
        )


class StubConnectionDetector:
    def __init__(self) -> None:
        self.detect = Mock(return_value=tuple())


class StubTextExtractor:
    def __init__(self) -> None:
        self.extract_text = Mock(return_value="")


class StubGraphBuilder:
    def __init__(self) -> None:
        graph = Mock()
        graph.node_count = 0
        graph.edge_count = 0
        self.build = Mock(return_value=graph)


def test_processing_start_endpoint_triggers_processing_pipeline() -> None:
    storage = StubFileStorage()
    converter = StubImageConverter()
    detector = StubDiagramDetector()
    connection_detector = StubConnectionDetector()
    extractor = StubTextExtractor()
    graph_builder = StubGraphBuilder()

    processor = DiagramUploadProcessor(
        file_storage=storage,
        image_converter=converter,
        diagram_detector=detector,
        connection_detector=connection_detector,
        text_extractor=extractor,
        graph_builder=graph_builder,
    )
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor.process, error_report_publisher=reporter))

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
    assert response.json()["status"] == "accepted"
    assert response.json()["protocol"] == "550e8400-e29b-41d4-a716-446655440000"

    storage.download_file.assert_called_once_with(
        file_url="s3://input-bucket/uploads/project-a/diagram.pdf"
    )
    converter.convert_to_image.assert_called_once_with(file_content=b"pdf-bytes", extension=".pdf")


def test_processing_start_endpoint_does_not_require_sqs_listener() -> None:
    processor = AsyncMock()
    reporter = AsyncMock()
    client = TestClient(create_app(processor=processor, error_report_publisher=reporter))

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440001",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 202
    processor.assert_awaited_once()


def test_processing_start_endpoint_returns_problem_details_with_expected_media_type() -> None:
    processor = AsyncMock(side_effect=RuntimeError("unexpected internal error"))
    reporter = AsyncMock()
    client = TestClient(
        create_app(processor=processor, error_report_publisher=reporter),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/processing-start",
        json={
            "protocol": "550e8400-e29b-41d4-a716-446655440009",
            "file": {
                "url": "s3://input-bucket/uploads/project-a/diagram.pdf",
                "mimetype": "application/pdf",
            },
        },
    )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 500
    assert body["instance"] == "/processing-start"
