#!/usr/bin/env python3
"""Quick script to fix test_diagram_upload_processor.py by adding connection_detector."""

file_path = "tests/unit/core/application/services/test_diagram_upload_processor.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to find and replace
old_pattern = """    mock_extractor = MockTextExtractor()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        diagram_detector=mock_detector,
        text_extractor=mock_extractor,
    )"""

new_pattern = """    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        diagram_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
    )"""

# Replace all occurrences
content = content.replace(old_pattern, new_pattern)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Fixed {file_path}")
