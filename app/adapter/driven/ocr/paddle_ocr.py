from io import BytesIO
from typing import Any

import numpy as np
import structlog
from PIL import Image

from app.core.application.exceptions import TextExtractionError

logger = structlog.get_logger()


class PaddleOCRExtractor:
    """PaddleOCR implementation of the TextExtractor port."""

    def __init__(self, ocr_engine: Any, use_angle_cls: bool = True):
        """Initialize the PaddleOCR extractor.

        Args:
            ocr_engine: Configured PaddleOCR engine instance
            use_angle_cls: Whether to enable angle classification for legacy ocr() API
        """
        self.ocr_engine = ocr_engine
        self.use_angle_cls = use_angle_cls

    def extract_text(
        self,
        image_bytes: bytes,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> str:
        """Extract text from a specific image region using PaddleOCR."""
        logger.info(
            "paddle.extract_text.start",
            x=x,
            y=y,
            width=width,
            height=height,
        )

        if width <= 0 or height <= 0:
            logger.info(
                "paddle.extract_text.zero_dimensions",
                width=width,
                height=height,
            )
            return ""

        try:
            cropped_image = self._crop_region(image_bytes, x, y, width, height)
            if cropped_image is None:
                return ""

            text_lines = self._recognize_lines(cropped_image)
            extracted_text = " ".join(line for line in text_lines if line).strip()

            logger.info(
                "paddle.extract_text.success",
                text_length=len(extracted_text),
                line_count=len(text_lines),
            )
            return extracted_text
        except TextExtractionError:
            raise
        except Exception as error:
            logger.error(
                "paddle.extract_text.error",
                error=str(error),
                exc_info=True,
            )
            raise TextExtractionError(f"Failed to extract text from image: {error}") from error

    def _crop_region(
        self,
        image_bytes: bytes,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> np.ndarray | None:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        left = max(0, int(x))
        top = max(0, int(y))
        right = min(image.width, int(x + width))
        bottom = min(image.height, int(y + height))

        if right <= left or bottom <= top:
            logger.info(
                "paddle.extract_text.invalid_crop",
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )
            return None

        cropped = image.crop((left, top, right, bottom))
        cropped_array = np.array(cropped)

        logger.debug(
            "paddle.extract_text.image_cropped",
            original_size=image.size,
            cropped_size=cropped.size,
        )
        return cropped_array

    def _recognize_lines(self, cropped_image: np.ndarray) -> list[str]:
        predict = getattr(self.ocr_engine, "predict", None)
        if callable(predict):
            try:
                predict_result = predict(cropped_image)
                lines = self._parse_predict_result(predict_result)
                if lines:
                    return lines
            except Exception as error:
                logger.warning(
                    "paddle.extract_text.predict_failed",
                    error=str(error),
                )

        ocr = getattr(self.ocr_engine, "ocr", None)
        if callable(ocr):
            ocr_result = ocr(cropped_image, cls=self.use_angle_cls)
            return self._parse_legacy_ocr_result(ocr_result)

        raise TextExtractionError("Failed to extract text using PaddleOCR: no compatible OCR method")

    def _parse_predict_result(self, result: Any) -> list[str]:
        lines: list[str] = []

        for item in self._as_iterable(result):
            if item is None:
                continue

            rec_texts = None
            if isinstance(item, dict):
                rec_texts = item.get("rec_texts") or item.get("texts") or item.get("text")
            else:
                for attribute in ("rec_texts", "texts", "text"):
                    if hasattr(item, attribute):
                        rec_texts = getattr(item, attribute)
                        if rec_texts:
                            break

            if rec_texts is None:
                continue

            if isinstance(rec_texts, str):
                stripped = rec_texts.strip()
                if stripped:
                    lines.append(stripped)
                continue

            for text in self._as_iterable(rec_texts):
                if isinstance(text, str):
                    stripped = text.strip()
                    if stripped:
                        lines.append(stripped)

        return lines

    def _parse_legacy_ocr_result(self, result: Any) -> list[str]:
        lines: list[str] = []

        for page in self._as_iterable(result):
            for detection in self._as_iterable(page):
                if not isinstance(detection, (list, tuple)) or len(detection) < 2:
                    continue

                text_with_score = detection[1]
                if not isinstance(text_with_score, (list, tuple)) or not text_with_score:
                    continue

                candidate = text_with_score[0]
                if isinstance(candidate, str):
                    stripped = candidate.strip()
                    if stripped:
                        lines.append(stripped)

        return lines

    @staticmethod
    def _as_iterable(value: Any) -> list[Any]:
        if isinstance(value, (list, tuple)):
            return list(value)
        if value is None:
            return []
        return [value]
