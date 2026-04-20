from urllib.error import HTTPError

import pytest

from app.adapter.driven.detection.yolo_inference_client import (
    InferenceDetection,
    YoloInferenceClient,
    YoloInferenceClientError,
)


class _FakeHttpResponse:
    def __init__(self, status_code: int, payload: bytes):
        self._status_code = status_code
        self._payload = payload

    def getcode(self) -> int:
        return self._status_code

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_yolo_inference_client_parses_response_contract(monkeypatch: pytest.MonkeyPatch):
    client = YoloInferenceClient(base_url="http://example.test:8000")

    def fake_urlopen(request, timeout):
        return _FakeHttpResponse(
            200,
            b'{"detections":[{"label":"service","bbox":{"x1":10,"y1":20,"x2":110,"y2":220}}]}',
        )

    monkeypatch.setattr(
        "app.adapter.driven.detection.yolo_inference_client.urlopen",
        fake_urlopen,
    )

    detections = client.infer(b"png-bytes")

    assert detections == (
        InferenceDetection(
            label="service",
            x1=10.0,
            y1=20.0,
            x2=110.0,
            y2=220.0,
            confidence=1.0,
        ),
    )


def test_yolo_inference_client_uses_cache_for_same_image_bytes(monkeypatch: pytest.MonkeyPatch):
    client = YoloInferenceClient(base_url="http://example.test:8000")
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        return _FakeHttpResponse(200, b'{"detections":[]}')

    monkeypatch.setattr(
        "app.adapter.driven.detection.yolo_inference_client.urlopen",
        fake_urlopen,
    )

    assert client.infer(b"same-image") == tuple()
    assert client.infer(b"same-image") == tuple()
    assert call_count == 1


def test_yolo_inference_client_raises_for_invalid_payload(monkeypatch: pytest.MonkeyPatch):
    client = YoloInferenceClient(base_url="http://example.test:8000")

    monkeypatch.setattr(
        "app.adapter.driven.detection.yolo_inference_client.urlopen",
        lambda request, timeout: _FakeHttpResponse(200, b'{"invalid":true}'),
    )

    with pytest.raises(YoloInferenceClientError, match="detections"):
        client.infer(b"png-bytes")


def test_yolo_inference_client_raises_for_http_error(monkeypatch: pytest.MonkeyPatch):
    client = YoloInferenceClient(base_url="http://example.test:8000")

    def raise_http_error(request, timeout):
        raise HTTPError(
            url="http://example.test:8000/infer",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        "app.adapter.driven.detection.yolo_inference_client.urlopen",
        raise_http_error,
    )

    with pytest.raises(YoloInferenceClientError, match="HTTP 503"):
        client.infer(b"png-bytes")
