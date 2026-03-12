from typing import Protocol


class TextExtractor(Protocol):
    """Port for text extraction operations from image regions (driven adapter interface)."""

    def extract_text(
        self,
        image_bytes: bytes,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> str:
        """Extract text from a specific region of an image using OCR.

        Args:
            image_bytes: PNG image content as bytes
            x: Bounding box top-left x-coordinate (pixels)
            y: Bounding box top-left y-coordinate (pixels)
            width: Bounding box width (pixels)
            height: Bounding box height (pixels)

        Returns:
            Extracted text from the image region, or empty string if no text detected

        Raises:
            TextExtractionError: If the OCR operation fails
        """
        ...
