from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class InferenceDetection:
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0


class YoloInferenceClientError(RuntimeError):
    """Raised when the remote YOLO inference API request/response fails."""


class YoloInferenceClient:
    def __init__(
        self,
        base_url: str,
        infer_path: str = "/infer",
        timeout_seconds: float = 10.0,
    ):
        normalized_base_url = base_url.rstrip("/") + "/"
        normalized_path = infer_path if infer_path.startswith("/") else f"/{infer_path}"

        self.infer_url = urljoin(normalized_base_url, normalized_path.lstrip("/"))
        self.timeout_seconds = timeout_seconds
        self._cache_lock = Lock()
        self._last_hash: str | None = None
        self._last_detections: tuple[InferenceDetection, ...] | None = None

    def infer(self, image_bytes: bytes) -> tuple[InferenceDetection, ...]:
        if not image_bytes:
            raise YoloInferenceClientError("Missing image bytes")

        image_hash = sha256(image_bytes).hexdigest()
        with self._cache_lock:
            if self._last_hash == image_hash and self._last_detections is not None:
                return self._last_detections

        detections = self._request_inference(image_bytes)
        with self._cache_lock:
            self._last_hash = image_hash
            self._last_detections = detections
        return detections

    def _request_inference(self, image_bytes: bytes) -> tuple[InferenceDetection, ...]:
        body, content_type = self._build_multipart_body(image_bytes)

        request = Request(
            url=self.infer_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": content_type,
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = response.getcode()
                payload = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise YoloInferenceClientError(
                f"Inference API returned HTTP {error.code}: {detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise YoloInferenceClientError(f"Inference API request failed: {error}") from error
        except OSError as error:
            raise YoloInferenceClientError(f"Inference API request failed: {error}") from error

        if status_code >= 400:
            raise YoloInferenceClientError(
                f"Inference API returned HTTP {status_code}: {payload}"
            )

        try:
            raw = json.loads(payload)
        except json.JSONDecodeError as error:
            raise YoloInferenceClientError("Inference API returned invalid JSON payload") from error

        return self._parse_detections(raw)

    def _parse_detections(self, payload: object) -> tuple[InferenceDetection, ...]:
        if not isinstance(payload, dict):
            raise YoloInferenceClientError("Inference API payload must be an object")

        raw_detections = payload.get("detections")
        if not isinstance(raw_detections, list):
            raise YoloInferenceClientError("Inference API payload missing 'detections' list")

        detections: list[InferenceDetection] = []
        for raw_detection in raw_detections:
            if not isinstance(raw_detection, dict):
                raise YoloInferenceClientError("Detection item must be an object")

            label = raw_detection.get("label")
            bbox = raw_detection.get("bbox")
            if not isinstance(label, str) or not label.strip():
                raise YoloInferenceClientError("Detection label must be a non-empty string")
            if not isinstance(bbox, dict):
                raise YoloInferenceClientError("Detection bbox must be an object")

            try:
                x1 = float(bbox["x1"])
                y1 = float(bbox["y1"])
                x2 = float(bbox["x2"])
                y2 = float(bbox["y2"])
            except (KeyError, TypeError, ValueError) as error:
                raise YoloInferenceClientError(
                    "Detection bbox must include numeric x1, y1, x2 and y2"
                ) from error

            detections.append(
                InferenceDetection(
                    label=label.strip(),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

        logger.info("yolo_inference_client.request_succeeded", detection_count=len(detections))
        return tuple(detections)

    @staticmethod
    def _build_multipart_body(image_bytes: bytes) -> tuple[bytes, str]:
        boundary = f"----diagram-analyzer-{uuid.uuid4().hex}"
        line_break = b"\r\n"

        body = bytearray()
        body.extend(f"--{boundary}".encode("utf-8"))
        body.extend(line_break)
        body.extend(b'Content-Disposition: form-data; name="file"; filename="diagram.png"')
        body.extend(line_break)
        body.extend(b"Content-Type: image/png")
        body.extend(line_break)
        body.extend(line_break)
        body.extend(image_bytes)
        body.extend(line_break)
        body.extend(f"--{boundary}--".encode("utf-8"))
        body.extend(line_break)

        return bytes(body), f"multipart/form-data; boundary={boundary}"
