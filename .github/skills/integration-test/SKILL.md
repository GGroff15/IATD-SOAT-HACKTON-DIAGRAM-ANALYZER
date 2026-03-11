---
name: integration-test
description: 'Write integration tests for the diagram analyzer service testing component interactions across hexagonal architecture layers. Use when verifying workflows between domain, application, and adapter layers with real implementations.'
argument-hint: 'Specify workflow: persistence, events, full-workflow, or adapter-integration'
---

# Integration Testing for Hexagonal Architecture

Test interactions between components using real implementations for layers under test. **Mock dependencies that aren't part of the integration** to keep tests fast, focused, and maintainable.

## Core Principle

**Integration tests verify specific layer interactions, not everything at once.**

- Test the integration between 2-3 components
- Use real implementations ONLY for the layers being tested
- Mock all other dependencies (other layers, external services)
- Keep tests fast (<100ms) by minimizing external calls

**Example:** When testing `DiagramUploadListener` (driver adapter):
- ✅ Real: Listener code, SQS client (testcontainers), message parsing
- ❌ Mock: Processor (application layer), Repository, Event publishers

This isolates what you're testing and prevents test failures from unrelated components.

## Benefits of Mocking Non-Tested Layers

1. **Faster tests:** No waiting for slow operations or external services
2. **Focused failures:** Test fails only when the integration under test breaks
3. **Easier debugging:** Smaller scope makes issues easier to identify
4. **Better isolation:** Changes to mocked layers don't break these tests
5. **Predictable:** Mocks provide consistent, deterministic behavior

## When to Use This Skill

- Verifying workflows across multiple layers (domain → application → adapter)
- Testing adapter implementations with real resources (temp files, in-memory databases)
- Validating that ports and adapters integrate correctly
- Testing end-to-end use cases without external dependencies
- Ensuring transaction boundaries work correctly
- Debugging integration issues between components
- Need examples of multi-layer test patterns

## Integration vs Unit vs E2E

| Test Type | Scope | Dependencies | Speed | When to Use |
|-----------|-------|--------------|-------|-------------|
| **Unit** | Single class/function | All mocked | Very fast (<10ms) | Test logic in isolation |
| **Integration** | Multiple components | Real for layers under test, mock external | Fast (10-100ms) | Test component interactions |
| **E2E** | Full system | External services | Slow (100ms-1s+) | Test through API/UI |

## Key Principle: Mock What You Don't Test

**Integration tests verify specific layer interactions, not everything at once.**

✅ **Keep Real:** Components and layers being tested
❌ **Mock:** External dependencies, other layers not under test, slow operations

**Example:** Testing `DiagramUploadListener` → `DiagramUploadProcessor`
- ✅ Real: Listener, SQS message parsing, entity creation
- ❌ Mock: Processor implementation (mocked with AsyncMock)
- ✅ Real: SQS client (but using testcontainers/localstack)

This isolates the integration being tested while keeping tests fast and focused.

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

## Integration Testing Workflow

### Step 1: Identify the Integration Scenario

Ask: "What workflow am I testing across which layers?"

**Common scenarios:**
- Application service + repository (persistence workflow)
- Application service + event publisher (event workflow)
- Event listener → service → repository (full inbound workflow)
- Multiple adapters working together

### Step 2: Determine Real vs Mock Components

**Golden Rule:** Only use real implementations for the layers you're integrating. Mock everything else.

Use **real implementations** for:
- ✅ The specific layers being integrated (e.g., adapter + application)
- ✅ Domain entities and value objects (always real - they're POJOs)
- ✅ In-process test resources (temp files, in-memory stores, testcontainers)

Use **mocks** for:
- ❌ Layers NOT part of the integration (if testing listener→service, mock the repository)
- ❌ External services (AWS, APIs, databases - unless using testcontainers)
- ❌ Slow operations (network calls, heavy computations)
- ❌ Side effects you want to verify but not execute (event publishing, notifications)

**Example Scenarios:**

| Integration Under Test | Keep Real | Mock |
|------------------------|-----------|------|
| **Listener → Processor** | Listener, SQS client (testcontainers), entity parsing | Processor business logic, repositories, event publishers |
| **Service → Repository** | Service logic, repository implementation, temp file storage | Event publishers, external APIs, notifications |
| **Service → Event Publisher** | Service logic, event publisher | Repository (or use in-memory), external services |
| **Full workflow: Listener → Service → Repository** | All layers, temp storage | Only external services outside the app |

### Step 3: Set Up Temporary Resources

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

### Step 4: Write the Integration Test

Follow the AAA pattern with realistic workflows.

## Layer Integration Patterns

### Pattern 0: Driver Adapter in Isolation (Mock Downstream Layers)

Test driver adapters (event listeners, API controllers) WITHOUT testing application/domain layers.

**Purpose:** Verify adapter correctly receives input, parses it, and calls the application layer.

```python
# tests/integration/test_diagram_upload_listener.py
import json
import threading
import time
from unittest.mock import AsyncMock
from uuid import uuid4

from app.adapter.driver.event_listeners.diagram_upload_listener import DiagramUploadListener


def test_diagram_upload_listener_integration(sqs_client):
    """Test listener receives SQS messages and calls processor correctly."""
    # Arrange - Real SQS client (testcontainers), mocked processor
    q = sqs_client.create_queue(QueueName="test-diagram-queue")
    queue_url = q["QueueUrl"]
    
    # Mock the processor - we're NOT testing application logic here
    mock_processor = AsyncMock()
    
    listener = DiagramUploadListener(
        queue_url=queue_url,
        sqs_client=sqs_client,
        processor=mock_processor,  # ← Mocked downstream dependency
    )
    
    t = threading.Thread(target=listener.start, daemon=True)
    t.start()
    
    try:
        # Act - Send message
        diagram_upload_id = str(uuid4())
        body = {"diagramUploadId": diagram_upload_id, "folder": "integration-folder"}
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))
        
        time.sleep(3)
        
        # Assert - Message consumed from queue
        attrs = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"]
        )
        approx = int(attrs.get("Attributes", {}).get("ApproximateNumberOfMessages", 0))
        assert approx == 0
        
        # Assert - Processor called with correct entity
        mock_processor.assert_called_once()
        upload_entity = mock_processor.call_args[0][0]
        assert str(upload_entity.diagram_upload_id) == diagram_upload_id
        assert upload_entity.folder == "integration-folder"
    finally:
        listener.stop()
        t.join(timeout=5)
```

**What this tests:**
- ✅ SQS message polling and retrieval
- ✅ JSON parsing and validation
- ✅ Entity creation from message data
- ✅ Calling the processor with correct parameters
- ✅ Message deletion after processing

**What this doesn't test (by design):**
- ❌ Processor business logic (tested in application layer tests)
- ❌ Repository operations (tested in persistence integration tests)
- ❌ Domain validation logic (tested in unit tests)

### Pattern 1: Application + Driven Adapter (Persistence)

Test that application service correctly interacts with repository.

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
    import asyncio
    
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

### Pattern 2: Application + Driven Adapter (Event Publishing)

Test that events are published correctly during workflows. Mock repository since persistence isn't being tested.

```python
# tests/integration/test_event_publishing_workflow.py
import pytest
from unittest.mock import Mock, AsyncMock, call
from datetime import datetime
from app.core.application.services.diagram_service import DiagramService
from app.core.domain.entities.diagram import Diagram

@pytest.fixture
def event_publisher_spy():
    """Provide a spy to track event publishing calls."""
    return Mock()

@pytest.fixture
def mock_repository():
    """Mock repository since we're testing events, not persistence."""
    repo = AsyncMock()
    # Configure mock to return diagrams as needed
    repo.save.return_value = None
    repo.get.return_value = Diagram(id="test-id", content=b"data", format="PNG")
    return repo

@pytest.fixture
def diagram_service_with_events(mock_repository, event_publisher_spy):
    """Provide service with MOCKED repo and REAL event publisher spy."""
    return DiagramService(
        repository=mock_repository,  # ← Mocked - not testing persistence
        event_publisher=event_publisher_spy  # ← Real spy - testing events
    )

@pytest.mark.asyncio
async def test_upload_publishes_diagram_uploaded_event(
    diagram_service_with_events,
    event_publisher_spy,
    mock_repository
):
    """Test that uploading a diagram publishes the correct event."""
    # Act
    diagram = await diagram_service_with_events.upload_diagram(
        b"content",
        "PNG"
    )
    
    # Assert - Event published
    event_publisher_spy.publish.assert_called_once_with(
        "diagram.uploaded",
        {
            "diagram_id": diagram.id,
            "format": "PNG",
            "timestamp": pytest.approx(datetime.now(), abs=1)
        }
    )
    
    # Assert - Repository called (integration verified)
    mock_repository.save.assert_called_once()

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

**Key Point:** Repository is mocked because we're testing the application→event_publisher integration, not persistence.

### Pattern 3: Driver + Application + Driven (Full Inbound Workflow)

Test complete inbound flow from event listener through to persistence.

```python
# tests/integration/test_full_inbound_workflow.py
import pytest
import json
import base64
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

### Pattern 4: Multiple Adapters Integration

Test scenarios where multiple adapters interact.

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

## Common Mocking Patterns for Integration Tests

### AsyncMock for Async Dependencies

Always use `AsyncMock` for async functions/methods:

```python
from unittest.mock import AsyncMock

# ❌ Wrong - will fail with "coroutine expected" error
mock_processor = Mock()

# ✅ Correct - for async functions
mock_processor = AsyncMock()
mock_processor.return_value = some_value  # Configure return

# Using it
listener = DiagramUploadListener(
    queue_url=queue_url,
    sqs_client=sqs_client,
    processor=mock_processor  # async callable
)
```

### Mock Repository Pattern

When testing application services without persistence:

```python
from unittest.mock import AsyncMock
from app.core.domain.entities.diagram import Diagram

@pytest.fixture
def mock_repository():
    """Mock repository for testing application logic."""
    repo = AsyncMock()
    
    # Configure common operations
    repo.save.return_value = None
    repo.get.return_value = Diagram(id="test-123", content=b"data", format="PNG")
    repo.find_all.return_value = []
    repo.delete.return_value = None
    
    return repo

# Use in test
async def test_service_with_mocked_repo(mock_repository):
    service = DiagramService(repository=mock_repository, event_publisher=Mock())
    
    # Test application logic
    await service.some_operation()
    
    # Verify repository was called correctly
    mock_repository.save.assert_called_once()
```

### Mock Event Publisher Pattern

When testing without event side effects:

```python
from unittest.mock import Mock

@pytest.fixture
def mock_event_publisher():
    """Mock event publisher to verify events without publishing."""
    publisher = Mock()
    publisher.publish.return_value = None
    return publisher

# Use in test
async def test_service_with_mocked_events(mock_event_publisher):
    service = DiagramService(
        repository=some_repo,
        event_publisher=mock_event_publisher
    )
    
    await service.upload_diagram(b"data", "PNG")
    
    # Verify event was published
    mock_event_publisher.publish.assert_called_once_with(
        "diagram.uploaded",
        {"diagram_id": "...", "format": "PNG"}
    )
```

### Spy Pattern (Track Calls on Real Objects)

When you need to verify calls but keep real behavior:

```python
from unittest.mock import Mock

@pytest.fixture
def event_publisher_spy():
    """Spy to track events while still 'publishing' them."""
    spy = Mock()
    spy.published_events = []
    
    def track_and_publish(event_type, payload):
        spy.published_events.append((event_type, payload))
        # Could also call real publisher here if needed
    
    spy.publish.side_effect = track_and_publish
    return spy

# Use in test
async def test_with_spy(event_publisher_spy):
    service = DiagramService(repository=repo, event_publisher=event_publisher_spy)
    
    await service.upload_diagram(b"data", "PNG")
    
    # Check tracked events
    assert len(event_publisher_spy.published_events) == 1
    assert event_publisher_spy.published_events[0][0] == "diagram.uploaded"
```

### Partial Mocking (Some Methods Real, Some Mocked)

When you want mostly real behavior with selective mocking:

```python
from unittest.mock import patch

async def test_with_partial_mock(real_repository):
    """Test with real repository but mock slow operations."""
    
    # Real repository but mock one slow method
    with patch.object(real_repository, 'expensive_operation', return_value='mocked'):
        service = DiagramService(repository=real_repository)
        
        result = await service.do_something()
        
        # Most operations use real repo, expensive one is mocked
        assert result is not None
```

## Decision Tree: What to Mock?

```
Is the component part of the integration you're testing?
│
├─ YES → Keep it real
│   │
│   └─ Does it need external services?
│       │
│       ├─ YES → Use testcontainers or in-memory alternative
│       └─ NO → Use real implementation
│
└─ NO → Mock it
    │
    └─ Is it async?
        │
        ├─ YES → Use AsyncMock
        └─ NO → Use Mock
```

**Examples:**

| Test Focus | Real | Mock |
|------------|------|------|
| Testing listener parsing | Listener, SQS (testcontainers) | Processor, repository, events |
| Testing service logic | Service | Repository, event publisher, external APIs |
| Testing persistence | Service, repository, temp storage | Event publisher, external APIs |
| Testing full workflow | All app layers, temp storage | Only true external services |

## Integration Test Fixtures

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

## Testing Transaction & State Management

Test that state changes happen atomically:

```python
@pytest.mark.asyncio
async def test_failed_analysis_does_not_mark_as_analyzed(diagram_service):
    """Test that if analysis fails, diagram state doesn't change."""
    from unittest.mock import patch
    
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
    import asyncio
    
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

## Testing Resource Cleanup

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

## Testing with Time Dependencies

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

## Testing Error Recovery

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

# Run specific workflow
pytest tests/integration/test_diagram_persistence_workflow.py

# With verbose output
pytest tests/integration/ -v

# With coverage
pytest tests/integration/ --cov=app --cov-report=term-missing

# Stop on first failure
pytest tests/integration/ -x

# Run in parallel (requires pytest-xdist)
pytest tests/integration/ -n auto
```

## Troubleshooting

**Tests interfering with each other:**
- Ensure each test uses independent tmp_path
- Check fixtures have correct scope (function, not module)
- Verify cleanup happens in fixtures

**Slow integration tests:**
- Profile with `pytest --durations=10`
- Consider if some dependencies should be mocked
- Check for unnecessary sleep/wait statements

**Flaky tests:**
- Review timing assumptions
- Check for race conditions in concurrent tests
- Add explicit ordering where needed

**Resource not cleaned up:**
- Use tmp_path fixture (auto-cleanup)
- Add explicit cleanup in fixture teardown
- Check for exceptions preventing cleanup
