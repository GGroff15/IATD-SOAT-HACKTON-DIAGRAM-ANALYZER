## Plan: Setup Testcontainers with LocalStack (S3 + SQS)

Set up testcontainer infrastructure with LocalStack for testing S3 and SQS interactions in integration and BDD tests. The setup will include pytest fixtures, Behave environment configuration, and working examples demonstrating AWS service interactions.

**Steps**

1. Create test directory structure following project conventions
   - Create `tests/unit/`, `tests/integration/`, `tests/e2e/` directories
   - Create `features/` directory for BDD tests with `steps/` subdirectory
   - Each test type gets its own `conftest.py`

2. Create root test configuration in `tests/conftest.py`
   - Common fixtures for AWS region, test bucket names, test queue names
   - Shared test constants following hexagonal architecture patterns

3. Create LocalStack fixtures in `tests/integration/conftest.py` (*depends on 1*)
   - Session-scoped `localstack_container` fixture (reuse container across tests)
   - Function-scoped S3 client fixture with automatic cleanup
   - Function-scoped SQS client fixture with automatic cleanup
   - Helper fixtures for creating/cleaning S3 buckets and SQS queues
   - Configure `.with_services("s3", "sqs")` to optimize startup time

4. Create example integration test for S3 workflow (*depends on 3*)
   - Test file: `tests/integration/test_s3_operations.py`
   - Test uploading object to S3
   - Test retrieving object from S3
   - Test listing objects in bucket
   - Demonstrate proper use of LocalStack fixtures and cleanup

5. Create example integration test for SQS workflow (*depends on 3*, *parallel with step 4*)
   - Test file: `tests/integration/test_sqs_operations.py`
   - Test sending message to queue
   - Test receiving message from queue
   - Test message deletion
   - Demonstrate queue lifecycle management

6. Setup Behave environment for BDD tests in `features/environment.py` (*depends on 1*)
   - `before_all`: Start LocalStack container
   - `after_all`: Stop and cleanup LocalStack container
   - `before_scenario`: Setup S3 and SQS clients, attach to context
   - `after_scenario`: Clean up all created buckets and queues

7. Create example BDD feature test (*depends on 6*)
   - Feature file: `features/diagram_storage.feature`
   - Gherkin scenario for uploading diagram to S3
   - Gherkin scenario for event-driven processing with SQS
   - Step definitions in `features/steps/aws_steps.py`
   - Demonstrate stakeholder-readable business language tests

8. Create pytest configuration for integration tests
   - Add pytest markers for integration and e2e tests in `pyproject.toml`
   - Configure test discovery patterns
   - Set appropriate timeout values for container startup

**Relevant files**

- [pyproject.toml](pyproject.toml) — Add pytest configuration and markers
- `tests/conftest.py` (new) — Root fixtures for shared test configuration
- `tests/integration/conftest.py` (new) — LocalStack container and client fixtures
- `tests/integration/test_s3_operations.py` (new) — Example S3 integration test
- `tests/integration/test_sqs_operations.py` (new) — Example SQS integration test
- `features/environment.py` (new) — Behave hooks for LocalStack lifecycle
- `features/diagram_storage.feature` (new) — Example BDD scenarios
- `features/steps/aws_steps.py` (new) — Step definitions for AWS operations
- [.github/instructions/testing.instructions.md](.github/instructions/testing.instructions.md) — Reference for testing patterns and conventions
- [.github/instructions/architecture.instructions.md](.github/instructions/architecture.instructions.md) — Reference hexagonal architecture patterns for adapters

**Verification**

1. Run integration tests: `pytest tests/integration/ -v` — All tests should pass
2. Verify LocalStack container lifecycle: Check container starts once (session scope), see cleanup logs
3. Run BDD tests: `behave features/ -v` — All scenarios should pass
4. Verify test isolation: Run same test twice, ensure no state leakage between runs
5. Check Docker cleanup: `docker ps -a` after tests — No orphaned containers remain
6. Verify test markers work: `pytest -m integration` — Only integration tests run

**Decisions**

- **Container scope:** Session-scoped container for performance (container reused across tests), function-scoped cleanup fixtures for isolation
- **Services:** Restricted to S3 and SQS only using `.with_services()` to optimize startup time
- **LocalStack version:** Using testcontainers default (latest stable), can pin to specific version if needed
- **Cleanup strategy:** Automatic cleanup in fixture teardown (pytest) and after_scenario hooks (Behave)
- **Test organization:** Integration tests use pytest directly, BDD tests use Behave with Gherkin for stakeholder-readable scenarios
- **Boto3 configuration:** Use `localstack_container.get_client()` helper method (simplest approach with automatic credential/endpoint handling)
- **Excluded from scope:** 
  - Textract integration (not requested)
  - Performance/load testing
  - Multi-region scenarios
  - Production deployment configuration

**Approved Decisions**

1. **LocalStack version:** Use testcontainers default (latest stable), will pin to specific version only if stability issues arise
2. **Parallel execution:** Not adding pytest-xdist initially, will add when test suite grows beyond 10 tests
3. **CI/CD integration:** Will address Docker-in-Docker setup when CI pipeline is configured
