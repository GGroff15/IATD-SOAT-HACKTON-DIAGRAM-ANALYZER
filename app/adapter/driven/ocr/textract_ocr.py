from io import BytesIO

import structlog
from botocore.exceptions import ClientError
from PIL import Image

from app.core.application.exceptions import TextExtractionError

logger = structlog.get_logger()


class TextractOCR:
    """AWS Textract implementation of TextExtractor port for extracting text from images."""

    def __init__(self, textract_client):
        """Initialize Textract OCR adapter.

        Args:
            textract_client: Boto3 Textract client instance
        """
        self.textract_client = textract_client

    def extract_text(
        self,
        image_bytes: bytes,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> str:
        """Extract text from a specific region of an image using AWS Textract.

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
        logger.info(
            "textract.extract_text.start",
            x=x,
            y=y,
            width=width,
            height=height,
        )

        # Handle zero dimensions - no text to extract
        if width <= 0 or height <= 0:
            logger.info(
                "textract.extract_text.zero_dimensions",
                width=width,
                height=height,
            )
            return ""

        try:
            # Load and crop image to bounding box
            image = Image.open(BytesIO(image_bytes))
            
            # Convert coordinates to integers for cropping
            left = int(x)
            top = int(y)
            right = int(x + width)
            bottom = int(y + height)
            
            # Crop image to bounding box
            cropped_image = image.crop((left, top, right, bottom))
            
            # Convert cropped image to bytes
            cropped_buffer = BytesIO()
            cropped_image.save(cropped_buffer, format="PNG")
            cropped_bytes = cropped_buffer.getvalue()
            
            logger.debug(
                "textract.extract_text.image_cropped",
                original_size=image.size,
                cropped_size=cropped_image.size,
                cropped_bytes_length=len(cropped_bytes),
            )
            
            # Call Textract OCR
            response = self.textract_client.detect_document_text(
                Document={"Bytes": cropped_bytes}
            )
            
            # Extract text from LINE blocks only
            text_lines = []
            for block in response.get("Blocks", []):
                if block.get("BlockType") == "LINE":
                    text = block.get("Text", "")
                    if text:
                        text_lines.append(text)
            
            # Join lines with spaces
            extracted_text = " ".join(text_lines)
            
            logger.info(
                "textract.extract_text.success",
                text_length=len(extracted_text),
                line_count=len(text_lines),
            )
            
            return extracted_text

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "textract.extract_text.client_error",
                error_code=error_code,
                error=str(e),
            )
            raise TextExtractionError(
                f"Failed to extract text using Textract: {error_code}"
            ) from e

        except Exception as e:
            logger.error(
                "textract.extract_text.error",
                error=str(e),
                exc_info=True,
            )
            raise TextExtractionError(
                f"Failed to extract text from image: {e}"
            ) from e
