from uuid import uuid4, UUID
import pytest

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


def test_diagram_analysis_result_valid_empty():
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid, components=tuple())
    assert result.diagram_upload_id == uid
    assert result.components == tuple()
    assert result.component_count == 0


def test_diagram_analysis_result_valid_with_components():
    uid = uuid4()
    component1 = DetectedComponent(
        class_name="person",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    component2 = DetectedComponent(
        class_name="car",
        confidence=0.87,
        x=300.0,
        y=400.0,
        width=150.0,
        height=100.0,
    )
    
    result = DiagramAnalysisResult(
        diagram_upload_id=uid,
        components=(component1, component2),
    )
    
    assert result.diagram_upload_id == uid
    assert len(result.components) == 2
    assert result.component_count == 2
    assert result.components[0] == component1
    assert result.components[1] == component2


def test_diagram_analysis_result_immutable():
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid)
    
    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        result.diagram_upload_id = uuid4()


def test_diagram_analysis_result_invalid_uuid_type():
    with pytest.raises(TypeError, match="diagram_upload_id must be a UUID"):
        DiagramAnalysisResult(diagram_upload_id="not-a-uuid", components=tuple())


def test_diagram_analysis_result_invalid_uuid_none():
    with pytest.raises(TypeError, match="diagram_upload_id must be a UUID"):
        DiagramAnalysisResult(diagram_upload_id=None, components=tuple())


def test_diagram_analysis_result_components_not_tuple():
    uid = uuid4()
    component = DetectedComponent(
        class_name="person",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    
    # Should raise TypeError if components is not a tuple
    with pytest.raises(TypeError, match="components must be a tuple"):
        DiagramAnalysisResult(diagram_upload_id=uid, components=[component])


def test_diagram_analysis_result_invalid_component_type():
    uid = uuid4()
    
    with pytest.raises(TypeError, match="all components must be DetectedComponent instances"):
        DiagramAnalysisResult(diagram_upload_id=uid, components=("not a component",))


def test_diagram_analysis_result_component_count_property():
    uid = uuid4()
    components = tuple(
        DetectedComponent(
            class_name=f"object_{i}",
            confidence=0.8,
            x=float(i * 10),
            y=float(i * 20),
            width=10.0,
            height=20.0,
        )
        for i in range(5)
    )
    
    result = DiagramAnalysisResult(diagram_upload_id=uid, components=components)
    assert result.component_count == 5
    assert len(result.components) == 5
