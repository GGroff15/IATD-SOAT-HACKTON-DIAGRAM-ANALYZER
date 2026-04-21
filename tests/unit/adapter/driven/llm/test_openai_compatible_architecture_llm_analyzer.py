from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.adapter.driven.llm.openai_compatible_architecture_llm_analyzer import (
    MistralArchitectureAnalyzer,
)
from app.core.application.exceptions import LlmInferenceError
from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.graph import Graph, GraphNode


def _build_graph() -> Graph:
    return Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            GraphNode(
                node_id=0,
                component=DetectedComponent(
                    class_name="service",
                    confidence=0.9,
                    x=10.0,
                    y=20.0,
                    width=100.0,
                    height=50.0,
                    extracted_text="Billing Service",
                ),
            ),
        ),
        edges=tuple(),
    )


@pytest.mark.asyncio
async def test_openai_compatible_analyzer_parses_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    analyzer = MistralArchitectureAnalyzer(
        api_key="test-key",
        base_url="https://example.test",
        model="mistral-7b-instruct",
    )

    response = Mock()
    response.status_code = 200
    response.text = "ok"
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"risks":["Sync coupling"],'
                        '"recommendations":["Overall moderate risk","Adopt async boundaries"]}'
                    )
                }
            }
        ]
    }

    async_client = AsyncMock()
    async_client.post = AsyncMock(return_value=response)
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = async_client
    async_context_manager.__aexit__.return_value = False

    monkeypatch.setattr(
        "app.adapter.driven.llm.openai_compatible_architecture_llm_analyzer.httpx.AsyncClient",
        lambda *args, **kwargs: async_context_manager,
    )

    result = await analyzer.analyze(
        graph=_build_graph(),
        validation_result=ArchitecturalValidationResult(
            diagram_upload_id=uuid4(),
            is_valid=True,
            violations=tuple(),
        ),
    )

    assert result.risks == ("Sync coupling",)
    assert result.recommendations[0] == "Overall moderate risk"


@pytest.mark.asyncio
async def test_openai_compatible_analyzer_moves_summary_to_first_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = MistralArchitectureAnalyzer(
        api_key="test-key",
        base_url="https://example.test",
        model="mistral-7b-instruct",
    )

    response = Mock()
    response.status_code = 200
    response.text = "ok"
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"summary":"Top-level summary","risks":[],"recommendations":["Detail A","Detail B"]}'
                    )
                }
            }
        ]
    }

    async_client = AsyncMock()
    async_client.post = AsyncMock(return_value=response)
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = async_client
    async_context_manager.__aexit__.return_value = False

    monkeypatch.setattr(
        "app.adapter.driven.llm.openai_compatible_architecture_llm_analyzer.httpx.AsyncClient",
        lambda *args, **kwargs: async_context_manager,
    )

    result = await analyzer.analyze(
        graph=_build_graph(),
        validation_result=ArchitecturalValidationResult(
            diagram_upload_id=uuid4(),
            is_valid=True,
            violations=tuple(),
        ),
    )

    assert result.recommendations[0] == "Top-level summary"


@pytest.mark.asyncio
async def test_openai_compatible_analyzer_raises_for_http_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = MistralArchitectureAnalyzer(
        api_key="test-key",
        base_url="https://example.test",
        model="mistral-7b-instruct",
    )

    response = Mock()
    response.status_code = 503
    response.text = "upstream unavailable"

    async_client = AsyncMock()
    async_client.post = AsyncMock(return_value=response)
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = async_client
    async_context_manager.__aexit__.return_value = False

    monkeypatch.setattr(
        "app.adapter.driven.llm.openai_compatible_architecture_llm_analyzer.httpx.AsyncClient",
        lambda *args, **kwargs: async_context_manager,
    )

    with pytest.raises(LlmInferenceError, match="HTTP 503"):
        await analyzer.analyze(
            graph=_build_graph(),
            validation_result=ArchitecturalValidationResult(
                diagram_upload_id=uuid4(),
                is_valid=True,
                violations=tuple(),
            ),
        )


@pytest.mark.asyncio
async def test_openai_compatible_analyzer_retries_without_response_format_for_schema_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = MistralArchitectureAnalyzer(
        api_key="test-key",
        base_url="https://example.test",
        model="mistral-7b-instruct",
    )

    first_response = Mock()
    first_response.status_code = 400
    first_response.text = '{"error":"response_format.json_schema must be an object"}'

    second_response = Mock()
    second_response.status_code = 200
    second_response.text = "ok"
    second_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"risks":["Cluster bottleneck"],'
                        '"recommendations":["Overall moderate risk","Refactor edge-heavy modules"]}'
                    )
                }
            }
        ]
    }

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[first_response, second_response])
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = async_client
    async_context_manager.__aexit__.return_value = False

    monkeypatch.setattr(
        "app.adapter.driven.llm.openai_compatible_architecture_llm_analyzer.httpx.AsyncClient",
        lambda *args, **kwargs: async_context_manager,
    )

    result = await analyzer.analyze(
        graph=_build_graph(),
        validation_result=ArchitecturalValidationResult(
            diagram_upload_id=uuid4(),
            is_valid=True,
            violations=tuple(),
        ),
    )

    assert result.risks == ("Cluster bottleneck",)
    assert result.recommendations[0] == "Overall moderate risk"
    assert async_client.post.call_count == 2
    first_call_payload = async_client.post.call_args_list[0].kwargs["json"]
    second_call_payload = async_client.post.call_args_list[1].kwargs["json"]
    assert "response_format" in first_call_payload
    assert "response_format" not in second_call_payload
