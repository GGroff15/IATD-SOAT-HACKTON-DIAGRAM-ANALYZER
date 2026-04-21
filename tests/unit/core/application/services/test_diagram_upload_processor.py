from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest

from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType, DetectedConnection
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.application.exceptions import (
    ArchitecturalValidationExecutionError,
    ImageConversionError,
    DiagramDetectionError,
    LlmInferenceError,
    TextExtractionError,
    ConnectionDetectionError,
)
from app.core.domain.entities.architectural_validation import (
    ArchitecturalRuleViolation,
    ArchitecturalValidationResult,
)
from app.core.domain.entities.llm_architecture_analysis import LlmArchitectureAnalysis


class MockFileStorage:
    """Mock file storage for testing"""
    def __init__(self):
        self.download_file = AsyncMock(return_value=b"mock file content")


class MockImageConverter:
    """Mock image converter for testing"""
    def __init__(self):
        self.convert_to_image = Mock(return_value=b"converted png content")


class MockDiagramDetector:
    """Mock diagram detector for testing"""
    def __init__(self):
        self.detect = Mock(return_value=DiagramAnalysisResult(
            diagram_upload_id=uuid4(),
            components=tuple(),
        ))


class MockConnectionDetector:
    """Mock connection detector for testing"""
    def __init__(self):
        self.detect = Mock(return_value=tuple())


class MockTextExtractor:
    """Mock text extractor for testing"""
    def __init__(self):
        self.extract_text = Mock(return_value="")


class MockGraphBuilder:
    """Mock graph builder for testing"""
    def __init__(self):
        graph = Mock()
        graph.diagram_upload_id = uuid4()
        graph.node_count = 0
        graph.edge_count = 0
        self.build = Mock(return_value=graph)


class MockGraphResultPublisher:
    """Mock graph result publisher for testing"""
    def __init__(self):
        self.publish_graph = AsyncMock()


class MockArchitecturalRulesValidator:
    """Mock architectural rules validator for testing"""

    def __init__(self):
        self.validate = Mock(
            return_value=ArchitecturalValidationResult(
                diagram_upload_id=uuid4(),
                is_valid=True,
                violations=tuple(),
            )
        )


class MockArchitectureLlmAnalyzer:
    """Mock architecture LLM analyzer for testing."""

    def __init__(self):
        self.analyze = AsyncMock(
            return_value=LlmArchitectureAnalysis(
                risks=("Excessive sync coupling between services",),
                recommendations=(
                    "Overall architecture has moderate risk concentrated in service coupling.",
                    "Reduce synchronous calls by introducing async integration boundaries.",
                ),
            )
        )


@pytest.mark.asyncio
async def test_processor_downloads_file():
    """Test that processor calls file storage to download the file"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/folder-x/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_storage.download_file.assert_called_once_with(file_url="s3://input-bucket/folder-x/diagram.pdf")


@pytest.mark.asyncio
async def test_processor_with_custom_extension():
    """Test that processor uses the correct extension"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/my-folder/diagram.png", extension=".png")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_storage.download_file.assert_called_once_with(file_url="s3://input-bucket/my-folder/diagram.png")


@pytest.mark.asyncio
async def test_processor_converts_file_after_download():
    """Test that processor calls image converter after downloading file"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_storage.download_file.return_value = b"original pdf content"
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_converter.convert_to_image.assert_called_once_with(
        file_content=b"original pdf content",
        extension=".pdf"
    )


@pytest.mark.asyncio
async def test_processor_handles_conversion_error():
    """Test that processor handles image conversion errors gracefully"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.side_effect = ImageConversionError("Conversion failed")
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act & Assert
    with pytest.raises(ImageConversionError, match="Conversion failed"):
        await processor.process(upload)


@pytest.mark.asyncio
async def test_processor_with_jpg_extension():
    """Test that processor handles JPG files correctly"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/images/diagram.jpg", extension=".jpg")
    mock_storage = MockFileStorage()
    mock_storage.download_file.return_value = b"jpg image content"
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_converter.convert_to_image.assert_called_once_with(
        file_content=b"jpg image content",
        extension=".jpg"
    )


@pytest.mark.asyncio
async def test_processor_calls_detector_after_conversion():
    """Test that processor calls diagram detector after image conversion"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_detector.detect.assert_called_once_with(
        diagram_upload_id=upload.diagram_upload_id,
        image_bytes=b"converted png bytes",
    )


@pytest.mark.asyncio
async def test_processor_handles_detection_error():
    """Test that processor handles detection errors gracefully"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_detector.detect.side_effect = DiagramDetectionError("Detection failed")
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act & Assert
    with pytest.raises(DiagramDetectionError, match="Detection failed"):
        await processor.process(upload)


@pytest.mark.asyncio
async def test_processor_completes_full_workflow():
    """Test that processor completes the full workflow: download -> convert -> detect"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_storage.download_file.return_value = b"original pdf content"
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=tuple(),
    )
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert - verify all steps were called in order
    mock_storage.download_file.assert_called_once()
    mock_converter.convert_to_image.assert_called_once()
    mock_detector.detect.assert_called_once()


@pytest.mark.asyncio
async def test_processor_extracts_text_from_detected_components():
    """Test that processor calls text extractor for each detected component"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    
    # Mock detector with two detected components
    component1 = DetectedComponent(
        class_name="button",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    component2 = DetectedComponent(
        class_name="label",
        confidence=0.85,
        x=300.0,
        y=400.0,
        width=200.0,
        height=30.0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component1, component2),
    )
    
    # Mock text extractor
    mock_extractor = MockTextExtractor()
    mock_extractor.extract_text.side_effect = ["Login Button", "Username"]
    mock_connection_detector = MockConnectionDetector()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert - verify text extractor was called for each component
    assert mock_extractor.extract_text.call_count == 2
    
    # Check first call
    first_call = mock_extractor.extract_text.call_args_list[0]
    assert first_call[1]["image_bytes"] == b"converted png bytes"
    assert first_call[1]["x"] == 100.0
    assert first_call[1]["y"] == 200.0
    assert first_call[1]["width"] == 150.0
    assert first_call[1]["height"] == 50.0
    
    # Check second call
    second_call = mock_extractor.extract_text.call_args_list[1]
    assert second_call[1]["image_bytes"] == b"converted png bytes"
    assert second_call[1]["x"] == 300.0
    assert second_call[1]["y"] == 400.0
    assert second_call[1]["width"] == 200.0
    assert second_call[1]["height"] == 30.0


@pytest.mark.asyncio
async def test_processor_enriches_components_with_extracted_text():
    """Test that processor adds extracted text to detected components"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    
    component = DetectedComponent(
        class_name="button",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component,),
    )
    
    mock_extractor = MockTextExtractor()
    mock_extractor.extract_text.return_value = "Submit Button"
    mock_connection_detector = MockConnectionDetector()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert - verify text extractor was called
    mock_extractor.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_processor_handles_ocr_error_gracefully():
    """Test that processor continues when OCR fails for a component"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    
    component = DetectedComponent(
        class_name="button",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component,),
    )
    
    # Mock text extractor to raise error
    mock_extractor = MockTextExtractor()
    mock_extractor.extract_text.side_effect = TextExtractionError("OCR failed")
    mock_connection_detector = MockConnectionDetector()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act - should not raise exception, should log and continue
    await processor.process(upload)
    
    # Assert - verify text extractor was called but error was handled
    mock_extractor.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_processor_handles_empty_components_list():
    """Test that processor handles empty components list gracefully"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=tuple(),
    )
    mock_extractor = MockTextExtractor()
    mock_connection_detector = MockConnectionDetector()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert - text extractor should not be called when no components
    mock_extractor.extract_text.assert_not_called()


@pytest.mark.asyncio
async def test_processor_detects_connections_after_components():
    """Test that processor calls connection detector after component detection"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    
    # Mock detector with detected components
    component = DetectedComponent(
        class_name="box",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component,),
    )
    
    # Mock connection detector
    mock_connection_detector = MockConnectionDetector()
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.85,
        start_point=(100.0, 200.0),
        end_point=(300.0, 400.0),
    )
    mock_connection_detector.detect.return_value = (connection,)
    
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act
    await processor.process(upload)
    
    # Assert - connection detector should be called with image and components
    mock_connection_detector.detect.assert_called_once_with(
        image_bytes=b"converted png bytes",
        components=(component,),
    )


@pytest.mark.asyncio
async def test_processor_handles_connection_detection_error_gracefully():
    """Test that processor continues when connection detection fails"""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    
    component = DetectedComponent(
        class_name="box",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component,),
    )
    
    # Mock connection detector to raise error
    mock_connection_detector = MockConnectionDetector()
    mock_connection_detector.detect.side_effect = ConnectionDetectionError("Detection failed")
    
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
    )
    
    # Act - should not raise exception, should log and continue
    await processor.process(upload)
    
    # Assert - connection detector was called but error was handled
    mock_connection_detector.detect.assert_called_once()


@pytest.mark.asyncio
async def test_processor_builds_graph_from_final_result():
    """Test that processor builds and publishes graph from final analysis result."""
    # Arrange
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"

    component = DetectedComponent(
        class_name="box",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.85,
        start_point=(100.0, 200.0),
        end_point=(300.0, 400.0),
        source_component_index=0,
        target_component_index=0,
    )
    mock_detector = MockDiagramDetector()
    mock_detector.detect.return_value = DiagramAnalysisResult(
        diagram_upload_id=upload.diagram_upload_id,
        components=(component,),
    )
    mock_connection_detector = MockConnectionDetector()
    mock_connection_detector.detect.return_value = (connection,)
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    mock_graph_result_publisher = MockGraphResultPublisher()
    mock_architectural_rules_validator = MockArchitecturalRulesValidator()
    mock_architectural_rules_validator.validate.return_value = ArchitecturalValidationResult(
        diagram_upload_id=upload.diagram_upload_id,
        is_valid=True,
        violations=tuple(),
    )

    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
        architectural_rules_validator=mock_architectural_rules_validator,
        graph_result_publisher=mock_graph_result_publisher,
    )

    # Act
    await processor.process(upload)

    # Assert
    assert mock_graph_builder.build.call_count == 1
    build_arg = mock_graph_builder.build.call_args[0][0]
    assert build_arg.diagram_upload_id == upload.diagram_upload_id
    assert build_arg.component_count == 1
    assert build_arg.connection_count == 1
    mock_architectural_rules_validator.validate.assert_called_once_with(
        mock_graph_builder.build.return_value
    )
    mock_graph_result_publisher.publish_graph.assert_awaited_once_with(
        mock_graph_builder.build.return_value,
        mock_architectural_rules_validator.validate.return_value,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_processor_continues_publishing_when_architectural_violations_exist():
    """Test that rule violations do not stop graph publishing."""
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    mock_graph_result_publisher = MockGraphResultPublisher()
    mock_architectural_rules_validator = MockArchitecturalRulesValidator()

    mock_architectural_rules_validator.validate.return_value = ArchitecturalValidationResult(
        diagram_upload_id=upload.diagram_upload_id,
        is_valid=False,
        violations=(
            ArchitecturalRuleViolation(
                code="ORPHAN_CONNECTION",
                message="Connection must reference both source and target components",
                edge_id=0,
            ),
        ),
    )

    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
        architectural_rules_validator=mock_architectural_rules_validator,
        graph_result_publisher=mock_graph_result_publisher,
    )

    await processor.process(upload)

    mock_graph_result_publisher.publish_graph.assert_awaited_once_with(
        mock_graph_builder.build.return_value,
        mock_architectural_rules_validator.validate.return_value,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_processor_raises_technical_validation_error_when_validator_crashes():
    """Test that unexpected validator errors are wrapped as technical failures."""
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    mock_architectural_rules_validator = MockArchitecturalRulesValidator()
    mock_architectural_rules_validator.validate.side_effect = RuntimeError("validator crashed")

    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
        architectural_rules_validator=mock_architectural_rules_validator,
    )

    with pytest.raises(ArchitecturalValidationExecutionError, match="validator crashed"):
        await processor.process(upload)


@pytest.mark.asyncio
async def test_processor_publishes_llm_analysis_when_available():
    """Test that processor includes LLM analysis in published payload."""
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    mock_graph_result_publisher = MockGraphResultPublisher()
    mock_architectural_rules_validator = MockArchitecturalRulesValidator()
    mock_llm_analyzer = MockArchitectureLlmAnalyzer()

    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
        architectural_rules_validator=mock_architectural_rules_validator,
        architecture_llm_analyzer=mock_llm_analyzer,
        graph_result_publisher=mock_graph_result_publisher,
    )

    await processor.process(upload)

    mock_llm_analyzer.analyze.assert_awaited_once_with(
        graph=mock_graph_builder.build.return_value,
        validation_result=mock_architectural_rules_validator.validate.return_value,
    )
    mock_graph_result_publisher.publish_graph.assert_awaited_once_with(
        mock_graph_builder.build.return_value,
        mock_architectural_rules_validator.validate.return_value,
        mock_llm_analyzer.analyze.return_value,
        None,
    )


@pytest.mark.asyncio
async def test_processor_continues_when_llm_fails_and_publishes_error_metadata():
    """Test that processor continues with LLM error metadata when inference fails."""
    upload = DiagramUpload(uuid4(), file_url="s3://input-bucket/test-folder/diagram.pdf", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_detector = MockDiagramDetector()
    mock_connection_detector = MockConnectionDetector()
    mock_extractor = MockTextExtractor()
    mock_graph_builder = MockGraphBuilder()
    mock_graph_result_publisher = MockGraphResultPublisher()
    mock_architectural_rules_validator = MockArchitecturalRulesValidator()
    mock_llm_analyzer = MockArchitectureLlmAnalyzer()
    mock_llm_analyzer.analyze.side_effect = LlmInferenceError("gateway timeout")

    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter,
        component_detector=mock_detector,
        connection_detector=mock_connection_detector,
        text_extractor=mock_extractor,
        graph_builder=mock_graph_builder,
        architectural_rules_validator=mock_architectural_rules_validator,
        architecture_llm_analyzer=mock_llm_analyzer,
        graph_result_publisher=mock_graph_result_publisher,
    )

    await processor.process(upload)

    publish_call_args = mock_graph_result_publisher.publish_graph.await_args.args
    assert publish_call_args[0] == mock_graph_builder.build.return_value
    assert publish_call_args[1] == mock_architectural_rules_validator.validate.return_value
    assert publish_call_args[2] is None
    assert publish_call_args[3].code == "LLM_INFERENCE_ERROR"
    assert publish_call_args[3].message == "gateway timeout"

