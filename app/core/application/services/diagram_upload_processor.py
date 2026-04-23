import structlog

from app.core.application.exceptions import FileStorageError
from app.core.application.exceptions import (
    ArchitecturalValidationExecutionError,
    LlmInferenceError,
)
from app.core.application.ports.architecture_llm_analyzer import ArchitectureLlmAnalyzer
from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import (
    LlmArchitectureAnalysis,
)
from app.core.application.ports.architectural_rules_validator import ArchitecturalRulesValidator
from app.core.application.ports.file_storage import FileStorage
from app.core.application.ports.image_converter import ImageConverter
from app.core.application.ports.diagram_detector import ComponentDetector
from app.core.application.ports.connection_detector import ConnectionDetector
from app.core.application.ports.text_extractor import TextExtractor
from app.core.application.ports.graph_result_publisher import GraphResultPublisher
from app.core.application.ports.graph_builder import GraphBuilder

logger = structlog.get_logger()


class DiagramUploadProcessor:
    """Application service for processing diagram upload events."""

    def __init__(
        self,
        file_storage: FileStorage,
        image_converter: ImageConverter,
        component_detector: ComponentDetector,
        connection_detector: ConnectionDetector,
        text_extractor: TextExtractor,
        graph_builder: GraphBuilder,
        architectural_rules_validator: ArchitecturalRulesValidator | None = None,
        architecture_llm_analyzer: ArchitectureLlmAnalyzer | None = None,
        graph_result_publisher: GraphResultPublisher | None = None,
    ):
        """Initialize the processor with injected dependencies.

        Args:
            file_storage: File storage adapter for downloading diagram files
            image_converter: Image converter adapter for normalizing file formats
            component_detector: Component detector adapter for identifying components
            connection_detector: Connection detector adapter for identifying connections
            text_extractor: Text extractor adapter for extracting text via OCR
            graph_builder: Graph builder service for constructing graph output
            architectural_rules_validator: Optional architectural rules validator
            architecture_llm_analyzer: Optional LLM analyzer for architecture risks/recommendations
            graph_result_publisher: Optional output adapter for graph publishing/persistence
        """
        self.file_storage = file_storage
        self.image_converter = image_converter
        self.component_detector = component_detector
        self.connection_detector = connection_detector
        self.text_extractor = text_extractor
        self.graph_builder = graph_builder
        self.architectural_rules_validator = architectural_rules_validator
        self.architecture_llm_analyzer = architecture_llm_analyzer
        self.graph_result_publisher = graph_result_publisher

    async def process(self, upload: DiagramUpload) -> None:
        """Process a diagram upload event by downloading and analyzing the diagram.

        Args:
            upload: The diagram upload entity with metadata
        """
        logger.info(
            "diagram_upload.process.received",
            diagram_upload_id=str(upload.diagram_upload_id),
            folder=upload.folder,
            file_url=upload.file_url,
            extension=upload.extension,
        )

        if not upload.file_url:
            raise FileStorageError("Diagram upload must include file_url for download")

        file_content = await self.file_storage.download_file(file_url=upload.file_url)
        
        logger.info(
            "diagram_upload.process.downloaded",
            diagram_upload_id=str(upload.diagram_upload_id),
            file_url=upload.file_url,
            size_bytes=len(file_content),
        )
        
        # Convert file to normalized PNG format
        image_bytes = self.image_converter.convert_to_image(
            file_content=file_content,
            extension=upload.extension,
        )
        
        logger.info(
            "diagram_upload.process.converted",
            diagram_upload_id=str(upload.diagram_upload_id),
            image_size_bytes=len(image_bytes),
        )
        
        # Detect components in the diagram
        analysis_result = self.component_detector.detect(
            diagram_upload_id=upload.diagram_upload_id,
            image_bytes=image_bytes,
        )
        
        logger.info(
            "diagram_upload.process.detected",
            diagram_upload_id=str(upload.diagram_upload_id),
            component_count=analysis_result.component_count,
        )
        
        # Detect connections between components
        connections: tuple = self.connection_detector.detect(
            image_bytes=image_bytes,
            components=analysis_result.components,
        )
        logger.info(
            "diagram_upload.process.connections_detected",
            diagram_upload_id=str(upload.diagram_upload_id),
            connection_count=len(connections),
        )
        
        # Extract text from each detected component
        enriched_components = []
        for component in analysis_result.components:
            extracted_text = self.text_extractor.extract_text(
                image_bytes=image_bytes,
                x=component.x,
                y=component.y,
                width=component.width,
                height=component.height,
            )
            logger.debug(
                "diagram_upload.process.text_extracted",
                diagram_upload_id=str(upload.diagram_upload_id),
                class_name=component.class_name,
                text_length=len(extracted_text),
            )
            
            enriched_component = DetectedComponent(
                class_name=component.class_name,
                confidence=component.confidence,
                x=component.x,
                y=component.y,
                width=component.width,
                height=component.height,
                extracted_text=extracted_text if extracted_text else None,
            )
            enriched_components.append(enriched_component)
        
        final_result = DiagramAnalysisResult(
            diagram_upload_id=upload.diagram_upload_id,
            components=tuple(enriched_components),
            connections=connections,
        )

        graph = self.graph_builder.build(final_result)
        validation_result = self._validate_architectural_rules(graph)
        llm_analysis = await self._analyze_with_llm(graph, validation_result)

        if self.graph_result_publisher is not None:
            await self.graph_result_publisher.publish_graph(
                graph,
                validation_result,
                llm_analysis
            )
        
        logger.info(
            "diagram_upload.process.completed",
            diagram_upload_id=str(upload.diagram_upload_id),
            component_count=final_result.component_count,
            connection_count=final_result.connection_count,
            components_with_text=sum(1 for c in enriched_components if c.extracted_text),
            graph_node_count=graph.node_count,
            graph_edge_count=graph.edge_count,
            architectural_is_valid=validation_result.is_valid,
            architectural_violation_count=len(validation_result.violations),
            llm_analysis_available=llm_analysis is not None,
        )

    def _validate_architectural_rules(self, graph: Graph) -> ArchitecturalValidationResult:
        if self.architectural_rules_validator is None:
            return ArchitecturalValidationResult(
                diagram_upload_id=graph.diagram_upload_id,
                is_valid=True,
                violations=tuple(),
            )

        try:
            validation_result = self.architectural_rules_validator.validate(graph)
        except Exception as error:  # pragma: no cover - exercised via unit test
            raise ArchitecturalValidationExecutionError(str(error)) from error

        logger.info(
            "diagram_upload.process.architectural_validation_completed",
            diagram_upload_id=str(graph.diagram_upload_id),
            is_valid=validation_result.is_valid,
            violation_count=len(validation_result.violations),
        )
        return validation_result

    async def _analyze_with_llm(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> LlmArchitectureAnalysis | None:
        if self.architecture_llm_analyzer is None:
            return None

        try:
            llm_analysis = await self.architecture_llm_analyzer.analyze(
                graph=graph,
                validation_result=validation_result,
            )
            
            return llm_analysis
        except LlmInferenceError as error:
            logger.warning(
                "diagram_upload.process.llm_analysis_failed",
                diagram_upload_id=str(graph.diagram_upload_id),
                error=str(error),
            )
            raise LlmInferenceError(f"LLM analysis failed: {error}") from error
