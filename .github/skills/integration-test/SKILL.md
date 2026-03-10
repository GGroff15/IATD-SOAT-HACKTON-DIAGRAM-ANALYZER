---
name: integration-test
description: 'Write integration tests for the diagram analyzer service testing component interactions across hexagonal architecture layers. Use when verifying workflows between domain, application, and adapter layers with real implementations.'
argument-hint: 'Specify workflow: persistence, events, full-workflow, or adapter-integration'
---

# Integration Testing for Hexagonal Architecture

Test interactions between components using real implementations where practical, verifying that layers work together correctly.

## When to Use

- Verifying workflows across multiple layers (domain → application → adapter)
- Testing adapter implementations with real resources (temp files, in-memory databases)
- Validating that ports and adapters integrate correctly
- Testing end-to-end use cases without external dependencies
- Ensuring transaction boundaries work correctly
- Debugging integration issues between components

## Integration vs Unit vs E2E

| Test Type | Scope | Dependencies | Speed | When to Use |
|-----------|-------|--------------|-------|-------------|
| **Unit** | Single class/function | All mocked | Very fast (<10ms) | Test logic in isolation |
| **Integration** | Multiple components | Real implementations (temp resources) | Fast (10-100ms) | Test component interactions |
| **E2E** | Full system | External services | Slow (100ms-1s+) | Test through API/UI |

## Structure

Place integration tests in `tests/integration/`:

```
tests/integration/
├── conftest.py                        # Integration test fixtures
├── test_diagram_persistence_workflow.py
├── test_diagram_analysis_workflow.py
├── test_event_publishing_workflow.py
└── test_repository_service_integration.py
```

**Naming:** `test_<workflow>_<layer_interaction>.py`

## Workflow

### 1. Identify the Integration Scenario

Ask: "What workflow am I testing across which layers?"

**Common scenarios:**
- Application service + repository (persistence workflow)
- Application service + event publisher (event workflow)
- Event listener → service → repository (full inbound workflow)
- Multiple adapters working together

### 2. Determine Real vs Mock Components

Use **real implementations** for:
- ✅ Components under test (services, repositories)
- ✅ Domain entities and value objects
- ✅ In-process resources (temp files, in-memory stores)

Use **mocks** for:
- ❌ External services (AWS, APIs, databases)
- ❌ Slow operations
- ❌ Components not part of the integration being tested

### 3. Set Up Temporary Resources

Use pytest fixtures for setup/teardown:

```python
@pytest.fixture
def temp_storage(tmp_path):
    """Provide temporary storage for integration tests."""
    storage_path = tmp_path / "diagrams"
    storage_path.mkdir()
    yield storage_path
    # Cleanup happens automatically with tmp_path
```

### 4. Write the Integration Test

Follow the AAA pattern with realistic workflows.

## Layer Integration Patterns

### Application + Driven Adapter (Persistence)

Test that application service correctly interacts with repository:

```python
# tests/integration/test_diagram_persistence_workflow.py
import pytest
from datetime import datetime
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository
from app.core.domain.entities.diagram import Diagram

@pytest.fixture
def file_repository(tmp_path):
    """Provide a real FileRepository with temporary storage."""
    return FileRepository(base_path=str(tmp_path / "diagrams"))

@pytest.fixture
def diagram_service(file_repository):
    """Provide DiagramService with real repository, mocked publisher."""
    from unittest.mock import Mock
    mock_publisher = Mock()
    return DiagramService(
        repository=file_repository,
        event_publisher=mock_publisher
    )

@pytest.mark.asyncio
async def test_upload_and_retrieve_diagram_workflow(diagram_service):
    """Test full workflow: upload diagram, save to storage, retrieve from storage."""
    # Arrange
    content = b"PNG\x89\x50\x4e\x47test image data"
    format_type = "PNG"
    
    # Act - Upload
    uploaded = await diagram_service.upload_diagram(content, format_type)
    diagram_id = uploaded.id
    
    # Act - Retrieve
    retrieved = await diagram_service.get_diagram(diagram_id)
    
    # Assert
    assert retrieved is not None
    assert retrieved.id == diagram_id
    assert retrieved.content == content
    assert retrieved.format == format_type
    assert retrieved.analyzed is False

@pytest.mark.asyncio
async def test_analyze_diagram_persists_state_change(diagram_service):
    """Test that analyzing a diagram persists the analyzed state."""
    # Arrange - Upload first
    diagram = await diagram_service.upload_diagram(b"test data", "PNG")
    diagram_id = diagram.id
    
    # Act - Analyze
    await diagram_service.analyze_diagram(diagram_id)
    
    # Act - Retrieve again
    updated = await diagram_service.get_diagram(diagram_id)
    
    # Assert - State persisted
    assert updated.analyzed is True

@pytest.mark.asyncio
async def test_concurrent_uploads_all_persist(diagram_service):
    """Test that multiple concurrent uploads all persist correctly."""
    # Arrange
    contents = [
        b"diagram 1 content",
        b"diagram 2 content",
        b"diagram 3 content"
    ]
    
    # Act - Upload concurrently
    upload_tasks = [
        diagram_service.upload_diagram(content, "PNG")
        for content in contents
    ]
    uploaded = await asyncio.gather(*upload_tasks)
    diagram_ids = [d.id for d in uploaded]
    
    # Act - Retrieve all
    retrieve_tasks = [
        diagram_service.get_diagram(did)
        for did in diagram_ids
    ]
    retrieved = await asyncio.gather(*retrieve_tasks)
    
    # Assert - All persisted correctly
    assert len(retrieved) == 3
    assert all(d is not None for d in retrieved)
    assert set(d.content for d in retrieved) == set(contents)
```

### Application + Driven Adapter (Event Publishing)

Test that events are published correctly during workflows:

```python
# tests/integration/test_event_publishing_workflow.py
import pytest
from unittest.mock import Mock, call
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository

@pytest.fixture
def event_publisher_spy():
    """Provide a spy to track event publishing calls."""
    return Mock()

@pytest.fixture
def diagram_service_with_events(tmp_path, event_publisher_spy):
    """Provide service with real repo and event publisher spy."""
    repo = FileRepository(base_path=str(tmp_path / "diagrams"))
    return DiagramService(repo, event_publisher_spy)

@pytest.mark.asyncio
async def test_upload_publishes_diagram_uploaded_event(
    diagram_service_with_events,
    event_publisher_spy
):
    """Test that uploading a diagram publishes the correct event."""
    # Act
    diagram = await diagram_service_with_events.upload_diagram(
        b"content",
        "PNG"
    )
    
    # Assert
    event_publisher_spy.publish.assert_called_once_with(
        "diagram.uploaded",
        {
            "diagram_id": diagram.id,
            "format": "PNG",
            "timestamp": pytest.approx(datetime.now(), abs=1)
        }
    )

@pytest.mark.asyncio
async def test_full_workflow_publishes_multiple_events(
    diagram_service_with_events,
    event_publisher_spy
):
    """Test that complete workflow publishes all expected events in order."""
    # Act
    diagram = await diagram_service_with_events.upload_diagram(b"data", "PNG")
    await diagram_service_with_events.analyze_diagram(diagram.id)
    
    # Assert - Verify event sequence
    assert event_publisher_spy.publish.call_count == 2
    calls = event_publisher_spy.publish.call_args_list
    
    # First event: upload
    assert calls[0][0][0] == "diagram.uploaded"
    assert calls[0][0][1]["diagram_id"] == diagram.id
    
    # Second event: analysis complete
    assert calls[1][0][0] == "diagram.analyzed"
    assert calls[1][0][1]["diagram_id"] == diagram.id
    assert calls[1][0][1]["result"] is not None
```

### Driver Adapter + Application + Driven Adapter (Full Workflow)

Test complete inbound flow from event listener through to persistence:

```python
# tests/integration/test_full_inbound_workflow.py
import pytest
from app.adapter.driver.event_listeners.sqs_handler import DiagramEventHandler
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository

@pytest.fixture
async def integrated_handler(tmp_path):
    """Provide a fully integrated event handler with real components."""
    # Real repository
    repo = FileRepository(base_path=str(tmp_path / "diagrams"))
    
    # Real service with real repo, mocked publisher
    from unittest.mock import Mock
    service = DiagramService(repo, Mock())
    
    # Real handler with real service
    handler = DiagramEventHandler(service)
    
    return handler

@pytest.mark.asyncio
async def test_handle_upload_event_end_to_end(integrated_handler):
    """Test handling an SQS message through full workflow to persistence."""
    # Arrange
    message = {
        "Records": [{
            "body": json.dumps({
                "diagram_id": "test-123",
                "s3_bucket": "my-bucket",
                "s3_key": "diagrams/test.png",
                "content": base64.b64encode(b"image data").decode()
            })
        }]
    }
    
    # Act
    await integrated_handler.handle(message)
    
    # Assert - Verify diagram was processed and persisted
    service = integrated_handler.service
    diagram = await service.get_diagram("test-123")
    
    assert diagram is not None
    assert diagram.id == "test-123"
    assert diagram.content == b"image data"

@pytest.mark.asyncio
async def test_invalid_message_does_not_corrupt_storage(integrated_handler):
    """Test that invalid messages fail gracefully without side effects."""
    # Arrange - Upload valid diagram first
    service = integrated_handler.service
    valid_diagram = await service.upload_diagram(b"valid", "PNG")
    
    # Act - Process invalid message
    invalid_message = {"Records": [{"body": "invalid json"}]}
    
    with pytest.raises(ValueError):
        await integrated_handler.handle(invalid_message)
    
    # Assert - Valid diagram still exists and is unchanged
    retrieved = await service.get_diagram(valid_diagram.id)
    assert retrieved is not None
    assert retrieved.content == b"valid"
```

### Multiple Adapters Integration

Test scenarios where multiple adapters interact:

```python
# tests/integration/test_multi_adapter_workflow.py
import pytest
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository
from app.adapter.driven.storage.s3_client import S3Client
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def multi_adapter_service(tmp_path):
    """Provide service with real file repo and mocked S3."""
    # Real local storage
    file_repo = FileRepository(base_path=str(tmp_path / "local"))
    
    # Mock remote storage
    mock_s3 = AsyncMock()
    mock_s3.upload.return_value = "s3://bucket/key"
    
    # Mock event publisher
    mock_publisher = Mock()
    
    return DiagramService(
        repository=file_repo,
        remote_storage=mock_s3,
        event_publisher=mock_publisher
    )

@pytest.mark.asyncio
async def test_diagram_archived_to_remote_after_analysis(multi_adapter_service):
    """Test workflow: upload → analyze → archive to S3."""
    # Arrange
    diagram = await multi_adapter_service.upload_diagram(b"content", "PNG")
    
    # Act
    await multi_adapter_service.analyze_diagram(diagram.id)
    await multi_adapter_service.archive_diagram(diagram.id)
    
    # Assert - Local and remote operations coordinated
    archived = await multi_adapter_service.get_diagram(diagram.id)
    assert archived.archived is True
    
    # Verify S3 interaction
    s3_client = multi_adapter_service.remote_storage
    s3_client.upload.assert_called_once()
```

## Fixtures for Integration Tests

Create specialized fixtures in `tests/integration/conftest.py`:

```python
# tests/integration/conftest.py
import pytest
from pathlib import Path
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository

@pytest.fixture
def integration_storage(tmp_path):
    """Provide temporary storage directory for integration tests."""
    storage = tmp_path / "integration_test_storage"
    storage.mkdir(parents=True)
    yield storage
    # Cleanup happens automatically

@pytest.fixture
def real_file_repository(integration_storage):
    """Provide a real FileRepository with temp storage."""
    return FileRepository(base_path=str(integration_storage))

@pytest.fixture
def event_spy():
    """Provide a mock that tracks all event publishing calls."""
    from unittest.mock import Mock
    spy = Mock()
    spy.published_events = []
    
    def track_publish(event_type, payload):
        spy.published_events.append((event_type, payload))
    
    spy.publish.side_effect = track_publish
    return spy

@pytest.fixture
def integrated_diagram_service(real_file_repository, event_spy):
    """Provide fully integrated DiagramService with real repo and event tracking."""
    return DiagramService(
        repository=real_file_repository,
        event_publisher=event_spy
    )

@pytest.fixture
async def sample_uploaded_diagram(integrated_diagram_service):
    """Provide a diagram that's already uploaded via the service."""
    return await integrated_diagram_service.upload_diagram(
        content=b"sample diagram content",
        format="PNG"
    )
```

## Transaction and State Management

Test that state changes happen atomically:

```python
@pytest.mark.asyncio
async def test_failed_analysis_does_not_mark_as_analyzed(diagram_service):
    """Test that if analysis fails, diagram state doesn't change."""
    # Arrange
    diagram = await diagram_service.upload_diagram(b"content", "PNG")
    
    # Act - Trigger analysis that will fail
    with patch("app.core.application.services.diagram_service.analyze_content") as mock_analyze:
        mock_analyze.side_effect = ValueError("Analysis failed")
        
        with pytest.raises(ValueError):
            await diagram_service.analyze_diagram(diagram.id)
    
    # Assert - State unchanged
    retrieved = await diagram_service.get_diagram(diagram.id)
    assert retrieved.analyzed is False

@pytest.mark.asyncio
async def test_concurrent_updates_maintain_consistency(diagram_service):
    """Test that concurrent operations maintain data consistency."""
    # Arrange
    diagram = await diagram_service.upload_diagram(b"content", "PNG")
    
    # Act - Concurrent operations
    tasks = [
        diagram_service.update_metadata(diagram.id, {"key": f"value{i}"})
        for i in range(10)
    ]
    await asyncio.gather(*tasks)
    
    # Assert - Final state is consistent
    retrieved = await diagram_service.get_diagram(diagram.id)
    assert retrieved is not None
    # Metadata should be one of the values, not corrupted
    assert "value" in retrieved.metadata.get("key", "")
```

## Resource Cleanup

Ensure tests clean up properly:

```python
@pytest.mark.asyncio
async def test_cleanup_after_workflow(diagram_service, integration_storage):
    """Test that cleanup properly removes all artifacts."""
    # Arrange - Create multiple diagrams
    diagrams = [
        await diagram_service.upload_diagram(b"content", "PNG")
        for _ in range(3)
    ]
    
    # Act - Delete all
    for diagram in diagrams:
        await diagram_service.delete_diagram(diagram.id)
    
    # Assert - Storage is clean
    remaining_files = list(integration_storage.glob("*"))
    assert len(remaining_files) == 0
```

## Common Patterns

### Testing with Time

```python
@pytest.mark.asyncio
async def test_diagram_expiry_workflow(diagram_service):
    """Test that diagrams expire after configured time."""
    from unittest.mock import patch
    from datetime import datetime, timedelta
    
    # Arrange - Upload with fixed time
    now = datetime(2026, 3, 10, 12, 0, 0)
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        diagram = await diagram_service.upload_diagram(b"content", "PNG")
    
    # Act - Advance time 7 days
    future = now + timedelta(days=7)
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = future
        active_diagrams = await diagram_service.get_active_diagrams()
    
    # Assert - Expired diagram not in active list
    assert diagram.id not in [d.id for d in active_diagrams]
```

### Testing Error Recovery

```python
@pytest.mark.asyncio
async def test_retry_on_transient_failure(diagram_service, real_file_repository):
    """Test that transient failures are retried automatically."""
    # Arrange - Mock repo to fail once then succeed
    original_save = real_file_repository.save
    call_count = 0
    
    async def flaky_save(diagram):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IOError("Transient error")
        return await original_save(diagram)
    
    real_file_repository.save = flaky_save
    
    # Act - Should succeed on retry
    diagram = await diagram_service.upload_diagram(b"content", "PNG")
    
    # Assert
    assert call_count == 2  # Failed once, succeeded on second try
    retrieved = await diagram_service.get_diagram(diagram.id)
    assert retrieved is not None
```

## Running Integration Tests

```bash
# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest tests/integration/ --cov=app

# Run specific workflow
pytest tests/integration/test_diagram_persistence_workflow.py

# Run with verbose output
pytest tests/integration/ -v

# Run parallel (if independent)
pytest tests/integration/ -n auto
```

## Integration Test Checklist

- [ ] Test realistic workflows across multiple components
- [ ] Use real implementations for components under test
- [ ] Use temporary resources (tmp_path) for storage
- [ ] Mock only external services and slow operations
- [ ] Verify state changes persist correctly
- [ ] Test both success and error paths
- [ ] Ensure proper cleanup (fixtures handle teardown)
- [ ] Tests remain fast (10-100ms target)
- [ ] Tests are independent (can run in any order)
- [ ] Document what integration is being tested

## Anti-Patterns to Avoid

❌ **Testing too much in one test**
```python
# Bad: Testing entire system
async def test_everything():
    # 50 lines of setup
    # Testing every feature
```

✅ **Focus on specific integration**
```python
# Good: Test one workflow
async def test_upload_and_retrieve_workflow(): ...
async def test_analyze_persists_state(): ...
```

❌ **Using real external services**
```python
# Bad: Calling real AWS
s3_client = boto3.client('s3')
```

✅ **Mock external, real internal**
```python
# Good: Mock external, real internal components
mock_s3 = AsyncMock()
real_file_repo = FileRepository(tmp_path)
```

❌ **Shared state between tests**
```python
# Bad: Module-level shared storage
storage = FileRepository("/tmp/shared")
```

✅ **Isolated resources per test**
```python
# Good: Fresh storage per test
@pytest.fixture
def storage(tmp_path):
    return FileRepository(tmp_path)
```

❌ **No cleanup**
```python
# Bad: Leaving artifacts
def test_upload():
    repo = FileRepository("/tmp")
    # No cleanup
```

✅ **Automatic cleanup with fixtures**
```python
# Good: Fixture handles cleanup
@pytest.fixture
def repo(tmp_path):
    yield FileRepository(tmp_path)
    # tmp_path cleanup automatic
```
