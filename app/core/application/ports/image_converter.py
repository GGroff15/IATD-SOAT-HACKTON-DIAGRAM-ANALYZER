from typing import Protocol


class ImageConverter(Protocol):
    """Port for image conversion operations (driven adapter interface)."""

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
        ...
