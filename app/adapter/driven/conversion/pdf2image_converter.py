from io import BytesIO
from typing import List

import structlog
from pdf2image import convert_from_bytes
from PIL import Image

from app.core.application.exceptions import (
    ImageConversionError,
    UnsupportedFileFormatError,
)

logger = structlog.get_logger()


class Pdf2ImageConverter:
    """Adapter for converting PDF and image files to normalized PNG format."""

    SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg"}
    SUPPORTED_FORMATS = {".pdf"} | SUPPORTED_IMAGE_FORMATS
    PDF_DPI = 300

    def convert_to_image(self, file_content: bytes, extension: str) -> bytes:
        """Convert a file to PNG image format.

        Handles PDF conversion and image format normalization:
        - PDF files: Converted to PNG at 300 DPI, multi-page PDFs merged vertically
        - Image files (.png, .jpg, .jpeg): Normalized to PNG format

        Args:
            file_content: The file content as bytes
            extension: The file extension (including the dot, e.g., '.pdf', '.png')

        Returns:
            PNG image content as bytes

        Raises:
            ImageConversionError: If the conversion operation fails
            UnsupportedFileFormatError: If the file format is not supported
        """
        normalized_ext = extension.lower()

        if normalized_ext not in self.SUPPORTED_FORMATS:
            raise UnsupportedFileFormatError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

        logger.info(
            "image_conversion.started",
            extension=extension,
            file_size_bytes=len(file_content),
        )

        try:
            if normalized_ext == ".pdf":
                result = self._convert_pdf(file_content)
            else:
                result = self._normalize_image(file_content)

            logger.info(
                "image_conversion.completed",
                extension=extension,
                output_size_bytes=len(result),
            )
            return result

        except (ImageConversionError, UnsupportedFileFormatError):
            raise
        except Exception as exc:
            logger.error(
                "image_conversion.failed",
                extension=extension,
                error=str(exc),
                exc_info=True,
            )
            raise ImageConversionError(
                f"Unexpected error during conversion: {exc}"
            ) from exc

    def _convert_pdf(self, pdf_content: bytes) -> bytes:
        """Convert PDF to PNG, merging multiple pages vertically.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            PNG image content as bytes

        Raises:
            ImageConversionError: If PDF conversion fails
        """
        try:
            logger.debug("pdf_conversion.converting", dpi=self.PDF_DPI)
            images = convert_from_bytes(pdf_content, dpi=self.PDF_DPI)
            logger.debug("pdf_conversion.pages_extracted", page_count=len(images))

            if len(images) == 1:
                # Single page PDF - convert directly
                return self._image_to_png_bytes(images[0])
            else:
                # Multi-page PDF - merge vertically
                merged_image = self._merge_images_vertically(images)
                return self._image_to_png_bytes(merged_image)

        except Exception as exc:
            logger.error("pdf_conversion.failed", error=str(exc), exc_info=True)
            raise ImageConversionError(f"Failed to convert PDF: {exc}") from exc

    def _normalize_image(self, image_content: bytes) -> bytes:
        """Normalize image to PNG format.

        Args:
            image_content: Image file content as bytes

        Returns:
            PNG image content as bytes

        Raises:
            ImageConversionError: If image loading or conversion fails
        """
        try:
            logger.debug("image_normalization.loading")
            image = Image.open(BytesIO(image_content))

            # Convert RGBA to RGB if necessary (JPEG doesn't support transparency)
            if image.mode in ("RGBA", "LA", "P"):
                # Create white background
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            logger.debug("image_normalization.converting", mode=image.mode, size=image.size)
            return self._image_to_png_bytes(image)

        except Exception as exc:
            logger.error("image_normalization.failed", error=str(exc), exc_info=True)
            raise ImageConversionError(f"Failed to convert image: {exc}") from exc

    def _merge_images_vertically(self, images: List[Image.Image]) -> Image.Image:
        """Merge multiple images vertically into a single image.

        Args:
            images: List of PIL Image objects to merge

        Returns:
            Single merged PIL Image object
        """
        # Calculate dimensions for merged image
        max_width = max(img.size[0] for img in images)
        total_height = sum(img.size[1] for img in images)

        logger.debug(
            "image_merge.merging",
            page_count=len(images),
            merged_width=max_width,
            merged_height=total_height,
        )

        # Create new image with combined dimensions
        merged = Image.new("RGB", (max_width, total_height), (255, 255, 255))

        # Paste each image at the appropriate vertical position
        current_y = 0
        for img in images:
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Center horizontally if image is narrower than max_width
            x_offset = (max_width - img.size[0]) // 2
            merged.paste(img, (x_offset, current_y))
            current_y += img.size[1]

        return merged

    def _image_to_png_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to PNG bytes.

        Args:
            image: PIL Image object

        Returns:
            PNG image content as bytes
        """
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
