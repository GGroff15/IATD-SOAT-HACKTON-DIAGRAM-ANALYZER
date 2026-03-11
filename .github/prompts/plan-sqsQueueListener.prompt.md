# Plan: SQS Queue Listener for Diagram Upload Events

Create an SQS listener to consume "diagram-uploaded" events with correlation ID tracking (Python MDC equivalent using structlog). The listener follows hexagonal architecture with domain, application, and adapter layers.

**TL;DR:** Implement event-driven processing of diagram uploads by creating an SQS long-polling listener, domain entity for diagram uploads, application service for processing, and structlog configuration for correlation ID tracking across all log statements.

## Steps

1. **Configure correlation ID logging infrastructure**
   - Create `app/infrastructure/logging/correlation.py` with `contextvars` for storing correlation IDs
   - Configure structlog in `app/infrastructure/logging/config.py` with `merge_contextvars` processor
   - Ensure all log statements automatically include correlation ID once set

2. **Define domain entity for diagram upload** (*parallel with step 1*)
   - Create `app/core/domain/entities/diagram_upload.py` with DiagramUpload entity
   - Properties: `diagram_upload_id: UUID`, `folder: str`
   - Implement validation in constructor (non-empty folder, valid UUID)

3. **Define application exceptions** (*parallel with step 1*)
   - Add to `app/core/application/exceptions.py`: 
     - `DiagramAnalyzerException` (base)
     - `InvalidMessageError` (malformed messages)
     - `ProcessingError` (processing failures)

4. **Create application service for processing uploads** (*depends on 2, 3*)
   - Create `app/core/application/services/diagram_upload_processor.py`
   - Method: `async def process_diagram_upload(upload: DiagramUpload) -> None`
   - For now, log the receipt with correlation ID (placeholder for future analysis logic)

5. **Create SQS listener adapter** (*depends on 1, 4*)
   - Create `app/adapter/driver/event_listeners/sqs_listener.py` with base `SQSListener` class
   - Long-polling pattern (WaitTimeSeconds=20, MaxNumberOfMessages=10)
   - Graceful shutdown handling (SIGTERM/SIGINT with threading.Event)
   - Generic message handling with error recovery

6. **Create diagram upload specific listener** (*depends on 5*)
   - Create `app/adapter/driver/event_listeners/diagram_upload_listener.py`
   - Extend base SQSListener
   - Parse JSON payload to DiagramUpload entity
   - Set correlation ID from `diagramUploadId` using contextvars
   - Call DiagramUploadProcessor service
   - Delete message on success, log errors on failure

7. **Configuration setup** (*parallel with steps 1-6*)
   - Create `app/infrastructure/config/settings.py` with Pydantic settings
   - Environment variables: `AWS_REGION`, `SQS_QUEUE_URL`, `AWS_ENDPOINT_URL` (for LocalStack)
   - Use python-dotenv for local development

8. **Update main.py to run listener** (*depends on 6, 7*)
   - Import and configure logging
   - Load settings from environment
   - Initialize listener with queue URL
   - Run listener with graceful shutdown

9. **Write unit tests** (*parallel with implementation steps*)
   - `tests/unit/core/domain/entities/test_diagram_upload.py` - entity validation
   - `tests/unit/core/application/services/test_diagram_upload_processor.py` - service logic with mocks
   - `tests/unit/adapter/driver/event_listeners/test_diagram_upload_listener.py` - message parsing, correlation ID binding

10. **Write integration tests** (*depends on 8*)
    - `tests/integration/test_diagram_upload_listener.py`
    - Use LocalStack fixture from existing conftest
    - Create queue, send message, verify processing
    - Verify correlation ID appears in logs

## Relevant Files

- `tests/integration/conftest.py` — reuse LocalStack fixtures for SQS testing
- `tests/integration/test_sqs_operations.py` — reference for SQS client usage patterns
- `features/environment.py` — reference for LocalStack setup in Behave tests
- `pyproject.toml` — boto3 and structlog already available, may need aioboto3 for async
- `main.py` — update to start the listener service

## Implementation Patterns to Follow

- **SQS Long-polling:** Use `WaitTimeSeconds=20` to reduce API calls
- **Correlation ID:** Use Python's `contextvars` + `structlog.contextvars.merge_contextvars` processor
- **Message deletion:** Only delete after successful processing  
- **Error handling:** Catch exceptions, log with correlation ID, let message return to queue for retry
- **Graceful shutdown:** Use `threading.Event` + signal handlers (SIGTERM/SIGINT)
- **Hexagonal architecture:** Keep domain pure, inject dependencies into application services

## Verification

1. Run unit tests: `pytest tests/unit/ -v`
2. Run integration test with LocalStack: `pytest tests/integration/test_diagram_upload_listener.py -v`
3. Manual test: Send JSON message `{"diagramUploadId": "<uuid>", "folder": "test-folder"}` to SQS queue using AWS CLI or console
4. Verify logs contain correlation ID in all log statements for that message
5. Verify message is deleted from queue after successful processing
6. Test graceful shutdown: `Ctrl+C` should log shutdown message and exit cleanly

## Decisions

- **Use sync boto3 initially (not async aioboto3)** — simpler to implement, sufficient for initial version, can add async later if needed
- **Single-threaded processing** — process messages sequentially in main thread, sufficient for MVP
- **Correlation ID from diagramUploadId** — reuse the upload ID as correlation ID for simplicity
- **Placeholder processing logic** — just log receipt for now, actual diagram analysis will be implemented later
- **No DLQ configuration initially** — rely on SQS visibility timeout and retries, can add DLQ later

## Further Considerations

1. **Should we add aioboto3 for async processing?** 
   - Option A: Start with sync boto3 (simpler, recommended for MVP)
   - Option B: Use aioboto3 with asyncio for concurrent message handling
   - **Recommendation:** Option A for initial implementation

2. **Should we configure a Dead Letter Queue (DLQ)?**
   - Option A: Add DLQ configuration to move failed messages after max retries
   - Option B: Rely on SQS default retry behavior initially
   - **Recommendation:** Option B initially, add DLQ in follow-up task

3. **Should we create BDD tests for this feature?**
   - Option A: Add behavior test "Given a diagram upload event, When listener receives it, Then it processes with correlation ID"
   - Option B: Integration tests are sufficient for infrastructure components
   - **Recommendation:** Option B - integration tests cover this infrastructure component adequately
