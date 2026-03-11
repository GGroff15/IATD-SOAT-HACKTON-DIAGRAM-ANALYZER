"""Integration tests for PDF to image conversion workflow."""
from io import BytesIO
import pytest
from PIL import Image
from pdf2image.exceptions import PDFInfoNotInstalledError

from app.adapter.driven.conversion.pdf2image_converter import Pdf2ImageConverter
from app.core.application.exceptions import (
    ImageConversionError,
    UnsupportedFileFormatError,
)


# Check if poppler is available
def check_poppler_available():
    """Check if poppler is installed and available."""
    try:
        from pdf2image import convert_from_bytes
        # Try a minimal conversion to check if poppler works
        test_pdf = b"%PDF-1.0\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        convert_from_bytes(test_pdf)
        return True
    except (PDFInfoNotInstalledError, FileNotFoundError):
        return False
    except Exception:
        # Other errors are fine - poppler is installed, just the test PDF is invalid
        return True


POPPLER_AVAILABLE = check_poppler_available()
requires_poppler = pytest.mark.skipif(
    not POPPLER_AVAILABLE,
    reason="Poppler not installed (required for pdf2image). Install poppler-utils or skip PDF tests."
)


@pytest.fixture
def converter():
    """Provide real Pdf2ImageConverter for integration testing."""
    return Pdf2ImageConverter()


@pytest.fixture
def sample_pdf_bytes():
    """Create a simple single-page PDF for testing."""
    # Create a simple PDF using reportlab if available, otherwise skip
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setFont("Helvetica", 16)
        pdf.drawString(100, 700, "Integration Test PDF")
        pdf.drawString(100, 650, "This is a test document")
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()
    except ImportError:
        pytest.skip("reportlab not installed, skipping PDF generation test")


@pytest.fixture
def sample_multipage_pdf_bytes():
    """Create a multi-page PDF for testing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # Page 1
        pdf.setFont("Helvetica", 16)
        pdf.drawString(100, 700, "Page 1")
        pdf.showPage()
        
        # Page 2
        pdf.drawString(100, 700, "Page 2")
        pdf.showPage()
        
        # Page 3
        pdf.drawString(100, 700, "Page 3")
        pdf.showPage()
        
        pdf.save()
        return buffer.getvalue()
    except ImportError:
        pytest.skip("reportlab not installed, skipping PDF generation test")


@pytest.fixture
def sample_real_png_bytes():
    """Create a real PNG image."""
    img = Image.new("RGB", (400, 300), color=(73, 109, 137))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_real_jpg_bytes():
    """Create a real JPEG image."""
    img = Image.new("RGB", (400, 300), color=(255, 100, 50))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@requires_poppler
def test_convert_real_pdf_to_png(converter, sample_pdf_bytes):
    """Integration test: Convert real PDF to PNG using pdf2image."""
    # Act
    result = converter.convert_to_image(sample_pdf_bytes, ".pdf")
    
    # Assert
    assert isinstance(result, bytes)
    assert len(result) > 0
    
    # Verify it's a valid PNG
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"
    assert img.mode == "RGB"
    assert img.size[0] > 0  # Has width
    assert img.size[1] > 0  # Has height

@requires_poppler

def test_convert_multipage_pdf_merges_vertically(converter, sample_multipage_pdf_bytes):
    """Integration test: Multi-page PDF is merged into single vertical image."""
    # Act
    result = converter.convert_to_image(sample_multipage_pdf_bytes, ".pdf")
    
    # Assert
    assert isinstance(result, bytes)
    
    # Verify the output
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"
    
    # Multi-page should result in a taller image (3 pages stacked)
    # Each page at 300 DPI from letter size should be ~2550x3300 pixels
    # Total height for 3 pages should be roughly 3 * 3300 = 9900 pixels
    assert img.size[1] > 8000, f"Expected tall merged image, got height: {img.size[1]}"


def test_normalize_real_png_image(converter, sample_real_png_bytes):
    """Integration test: Real PNG is normalized to consistent format."""
    # Act
    result = converter.convert_to_image(sample_real_png_bytes, ".png")
    
    # Assert
    assert isinstance(result, bytes)
    
    # Verify normalization
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"
    assert img.mode == "RGB"
    assert img.size == (400, 300)


def test_convert_real_jpg_to_png(converter, sample_real_jpg_bytes):
    """Integration test: Real JPEG is converted to PNG."""
    # Act
    result = converter.convert_to_image(sample_real_jpg_bytes, ".jpg")
    
    # Assert
    assert isinstance(result, bytes)
    
    # Verify conversion
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"
    assert img.mode == "RGB"
    assert img.size == (400, 300)

@requires_poppler

def test_invalid_pdf_bytes_raises_error(converter):
    """Integration test: Invalid PDF content raises ImageConversionError."""
    # Arrange
    invalid_pdf = b"This is not a valid PDF content"
    
    # Act & Assert
    with pytest.raises(ImageConversionError, match="Failed to convert PDF"):
        converter.convert_to_image(invalid_pdf, ".pdf")


def test_invalid_image_bytes_raises_error(converter):
    """Integration test: Invalid image content raises ImageConversionError."""
    # Arrange
    invalid_image = b"Not a valid image"
    
    # Act & Assert
    with pytest.raises(ImageConversionError, match="Failed to convert image"):
        converter.convert_to_image(invalid_image, ".png")


def test_unsupported_extension_raises_error(converter):
    """Integration test: Unsupported file extension raises UnsupportedFileFormatError."""
    # Arrange
    some_content = b"Some file content"
    
    # Act & Assert
    with pytest.raises(UnsupportedFileFormatError, match="Unsupported file format"):
        converter.convert_to_image(some_content, ".docx")


def test_case_insensitive_extensions(converter, sample_real_png_bytes):
    """Integration test: File extensions are case-insensitive."""
    # Act
    result_upper = converter.convert_to_image(sample_real_png_bytes, ".PNG")
    result_mixed = converter.convert_to_image(sample_real_png_bytes, ".PnG")
    
    # Assert
    assert isinstance(result_upper, bytes)
    assert isinstance(result_mixed, bytes)
    
    # Both should produce valid PNGs
    img_upper = Image.open(BytesIO(result_upper))
    img_mixed = Image.open(BytesIO(result_mixed))
    assert img_upper.format == "PNG"
    assert img_mixed.format == "PNG"
@requires_poppler


def test_pdf_conversion_preserves_aspect_ratio(converter, sample_pdf_bytes):
    """Integration test: PDF conversion maintains proper aspect ratio."""
    # Act
    result = converter.convert_to_image(sample_pdf_bytes, ".pdf")
    
    # Assert
    img = Image.open(BytesIO(result))
    
    # Letter size at 300 DPI should be approximately 2550 x 3300 pixels
    # Allow some variance for rounding
    expected_width = 2550
    expected_height = 3300
    tolerance = 100
    
    assert abs(img.size[0] - expected_width) < tolerance, \
        f"Width {img.size[0]} not close to expected {expected_width}"
    assert abs(img.size[1] - expected_height) < tolerance, \
        f"Height {img.size[1]} not close to expected {expected_height}"


def test_jpeg_extension_variant_works(converter, sample_real_jpg_bytes):
    """Integration test: .jpeg extension works like .jpg."""
    # Act
    result = converter.convert_to_image(sample_real_jpg_bytes, ".jpeg")
    
    # Assert
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"
    assert img.mode == "RGB"
