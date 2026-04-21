from unittest.mock import AsyncMock, Mock
import time
from uuid import UUID

from fastapi.testclient import TestClient

import app.adapter.driver.api.processing_start_endpoint as processing_start_endpoint
from app.adapter.driver.api.processing_start_endpoint import create_app
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult


def _wait_for(condition, timeout: float = 1.0, interval: float = 0.01) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()


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
        graph.diagram_upload_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        self.build = Mock(return_value=graph)


class StubArchitecturalRulesValidator:
    def __init__(self) -> None:
        self.validate = Mock(
            return_value=ArchitecturalValidationResult(
                diagram_upload_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                is_valid=True,
                violations=tuple(),
            )
        )


class StubGraphResultPublisher:
    def __init__(self) -> None:
        self.publish_graph = AsyncMock()


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
        component_detector=detector,
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

    assert _wait_for(lambda: storage.download_file.call_count == 1)
    assert _wait_for(lambda: converter.convert_to_image.call_count == 1)

    storage.download_file.assert_called_once_with(
        file_url="s3://input-bucket/uploads/project-a/diagram.pdf"
    )
    converter.convert_to_image.assert_called_once_with(file_content=b"pdf-bytes", extension=".pdf")


def test_processing_start_endpoint_uses_http_as_only_ingress() -> None:
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
    assert _wait_for(lambda: processor.await_count == 1)


def test_processing_start_endpoint_publishes_graph_with_validation_result() -> None:
    storage = StubFileStorage()
    converter = StubImageConverter()
    detector = StubDiagramDetector()
    connection_detector = StubConnectionDetector()
    extractor = StubTextExtractor()
    graph_builder = StubGraphBuilder()
    architectural_rules_validator = StubArchitecturalRulesValidator()
    graph_result_publisher = StubGraphResultPublisher()

    processor = DiagramUploadProcessor(
        file_storage=storage,
        image_converter=converter,
        component_detector=detector,
        connection_detector=connection_detector,
        text_extractor=extractor,
        graph_builder=graph_builder,
        architectural_rules_validator=architectural_rules_validator,
        graph_result_publisher=graph_result_publisher,
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
    assert _wait_for(lambda: graph_result_publisher.publish_graph.await_count == 1)
    graph_result_publisher.publish_graph.assert_awaited_once_with(
        graph_builder.build.return_value,
        architectural_rules_validator.validate.return_value,
        None,
        None,
    )


def test_processing_start_endpoint_returns_problem_details_with_expected_media_type(monkeypatch) -> None:
    processor = AsyncMock()
    reporter = AsyncMock()

    def _raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("unexpected internal error")

    monkeypatch.setattr(processing_start_endpoint.asyncio, "create_task", _raise_runtime_error)

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
    reporter.publish_error.assert_awaited_once()
