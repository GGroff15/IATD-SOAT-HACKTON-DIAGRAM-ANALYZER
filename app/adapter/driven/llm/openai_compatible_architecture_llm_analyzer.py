from __future__ import annotations

import json
from urllib.parse import urljoin

import httpx

from app.core.application.exceptions import LlmInferenceError
from app.core.application.ports.architecture_llm_analyzer import ArchitectureLlmAnalyzer
from app.core.application.services.mistral_architecture_prompt_builder import (
    MistralArchitecturePromptBuilder,
)
from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import LlmArchitectureAnalysis


class MistralArchitectureAnalyzer(ArchitectureLlmAnalyzer):
    """Driven adapter for Mistral Chat Completions inference."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        chat_completions_path: str = "/v1/chat/completions",
        timeout_seconds: float = 20.0,
        temperature: float = 0.1,
        max_tokens: int = 900,
        prompt_builder: MistralArchitecturePromptBuilder | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must be a non-empty string")
        if not model.strip():
            raise ValueError("model must be a non-empty string")

        normalized_base_url = base_url.rstrip("/") + "/"
        normalized_path = (
            chat_completions_path
            if chat_completions_path.startswith("/")
            else f"/{chat_completions_path}"
        )

        self._api_key = api_key
        self._url = urljoin(normalized_base_url, normalized_path.lstrip("/"))
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._prompt_builder = prompt_builder or MistralArchitecturePromptBuilder()

    async def analyze(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> LlmArchitectureAnalysis:
        messages = self._prompt_builder.build_messages(graph, validation_result)
        payload = {
            "model": self._model,
            "messages": list(messages),
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "risks": {
                             "type": "array",
                             "items": {"type": "string"},
                            },
                            "recommendations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "summary": {"type": "string"},
                        },
                        "required": ["risks", "recommendations"],
                    }
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._url, headers=headers, json=payload)
        except httpx.HTTPError as error:
            raise LlmInferenceError(f"LLM request failed: {error}") from error

        if response.status_code >= 400:
            raise LlmInferenceError(
                f"LLM request failed with HTTP {response.status_code}: {response.text}"
            )

        try:
            body = response.json()
        except ValueError as error:
            raise LlmInferenceError("LLM response is not valid JSON") from error

        content = self._extract_content(body)
        llm_payload = self._parse_json_content(content)
        risks, recommendations = self._normalize_output(llm_payload)

        return LlmArchitectureAnalysis(
            risks=tuple(risks),
            recommendations=tuple(recommendations),
        )

    @staticmethod
    def _extract_content(body: object) -> str:
        if not isinstance(body, dict):
            raise LlmInferenceError("LLM response body must be an object")

        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            raise LlmInferenceError("LLM response must contain choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LlmInferenceError("LLM choice item must be an object")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LlmInferenceError("LLM choice message must be an object")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmInferenceError("LLM message content must be a non-empty string")

        return content

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, object]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise LlmInferenceError("LLM content must be valid JSON") from error

        if not isinstance(parsed, dict):
            raise LlmInferenceError("LLM content JSON must be an object")
        return parsed

    @staticmethod
    def _normalize_output(parsed: dict[str, object]) -> tuple[list[str], list[str]]:
        risks_raw = parsed.get("risks", [])
        recommendations_raw = parsed.get("recommendations", [])
        summary_raw = parsed.get("summary")

        if not isinstance(risks_raw, list):
            raise LlmInferenceError("'risks' must be a list")
        if not isinstance(recommendations_raw, list):
            raise LlmInferenceError("'recommendations' must be a list")

        risks = MistralArchitectureAnalyzer._normalize_string_list(
            risks_raw, "risks"
        )
        recommendations = MistralArchitectureAnalyzer._normalize_string_list(
            recommendations_raw, "recommendations"
        )

        if summary_raw is not None:
            if not isinstance(summary_raw, str) or not summary_raw.strip():
                raise LlmInferenceError("'summary' must be a non-empty string when provided")
            summary = summary_raw.strip()
            remaining = [value for value in recommendations if value != summary]
            recommendations = [summary, *remaining]

        if len(recommendations) == 0:
            raise LlmInferenceError(
                "'recommendations' must include summary as the first list item"
            )

        return risks, recommendations

    @staticmethod
    def _normalize_string_list(values: list[object], field_name: str) -> list[str]:
        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise LlmInferenceError(
                    f"'{field_name}' items must be non-empty strings"
                )
            normalized.append(value.strip())
        return normalized
