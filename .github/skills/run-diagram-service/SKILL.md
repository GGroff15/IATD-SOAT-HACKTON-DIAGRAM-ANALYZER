---
name: run-diagram-service
description: 'Run, develop, and test the diagram analyzer microservice. Use when starting the service, installing dependencies, running tests, or working with the hexagonal architecture.'
argument-hint: 'Specify action: install, run, test, develop, or troubleshoot'
---

# Diagram Analyzer Service Development Workflow

Complete guide for running, developing, and testing the Python microservice for diagram analysis using hexagonal architecture.

## When to Use This Skill

- Setting up the project for the first time
- Starting the service in development mode
- Installing or updating dependencies with uv
- Running the test suite
- Understanding the development workflow
- Troubleshooting service startup or runtime issues
- Starting a new feature implementation
- Debugging test failures

## Prerequisites

- **Python:** 3.12 or higher
- **Package manager:** uv (install: `pip install uv`)
- **Virtual environment:** Created automatically by uv

## Quick Start

For first-time setup, run these commands in order:

```bash
# 1. Install dependencies
uv sync

# 2. Run the service
python main.py

# 3. Run tests
pytest
```

## Setup Workflow

### Step 1: Install Dependencies

First time setup or after `pyproject.toml` changes:

```bash
uv sync
```

**What this does:**
- Reads `pyproject.toml` for dependencies
- Creates `.venv/` virtual environment if it doesn't exist
- Installs all dependencies into `.venv/`
- Creates lock file for reproducible installs

**Install with dev dependencies:**

```bash
uv sync --extra dev
```

This includes testing tools (pytest, coverage), linters (ruff, black), and type checkers (mypy).

### Step 2: Activate Virtual Environment

**Windows PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**Unix/macOS:**
```bash
source .venv/bin/activate
```

**Note:** Many IDEs (VS Code, PyCharm) activate automatically.

### Step 3: Verify Installation

```bash
# Check Python version
python --version
# Should be 3.12+

# List installed packages
uv pip list

# Show specific package
uv pip show fastapi
```

## Running the Service

### Development Mode

Start the service from the main entry point:

```bash
python main.py
```

The service entry point is `main.py` in the project root.

**With auto-reload (if using uvicorn):**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

Create `.env` file in project root for configuration:

```bash
# .env
ENVIRONMENT=development
LOG_LEVEL=INFO
AWS_REGION=us-east-1
S3_BUCKET=diagram-uploads
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/diagrams
MAX_DIAGRAM_SIZE=10485760
```

Load with `python-dotenv` (already in dependencies).

## Running Tests

### All Tests

```bash
pytest
```

### By Test Type

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/
```

### By Layer

```bash
# Domain layer tests
pytest tests/unit/core/domain/

# Application layer tests
pytest tests/unit/core/application/

# Adapter tests
pytest tests/unit/adapter/
```

### Specific Tests

```bash
# Specific file
pytest tests/unit/core/application/test_diagram_service.py

# Specific test function
pytest tests/unit/core/application/test_diagram_service.py::test_upload_diagram_success

# Pattern matching
pytest -k "upload"  # runs all tests with "upload" in name
```

### With Coverage

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (opens browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html  # Unix/macOS
start htmlcov/index.html  # Windows
```

### Test Options

```bash
# Verbose output
pytest -v

# Very verbose (show print statements)
pytest -vv -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Show slowest tests
pytest --durations=10

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

## Development Workflow

### Starting a New Feature

1. **Understand the architecture layer:**
   - Domain logic? → `app/core/domain/`
   - Use case? → `app/core/application/services/`
   - External input? → `app/adapter/driver/`
   - External output? → `app/adapter/driven/`

2. **Write tests first (TDD):**
   ```bash
   # Create test file
   touch tests/unit/core/application/test_new_feature.py
   
   # Write failing test
   # Implement feature
   # Run test until it passes
   pytest tests/unit/core/application/test_new_feature.py
   ```

3. **Follow dependency rules:**
   - Dependencies flow inward: Adapters → Application → Domain
   - Domain has zero dependencies
   - Application depends only on domain
   - Inject adapters into services (dependency inversion)

4. **Run tests frequently:**
   ```bash
   # Watch mode (requires pytest-watch)
   pytest-watch
   ```

### Example: Adding a New Use Case

**Step-by-step workflow:**

1. **Define domain entity** (if needed):
   ```bash
   # Create in app/core/domain/entities/
   # No I/O, no framework dependencies
   ```

2. **Write application service** (use case):
   ```bash
   # Create in app/core/application/services/
   # Orchestrate domain + adapters
   # Define ports (interfaces) for adapters
   ```

3. **Implement adapters**:
   ```bash
   # Driver: app/adapter/driver/ (inbound)
   # Driven: app/adapter/driven/ (outbound)
   # Implement ports defined by application layer
   ```

4. **Write tests at each layer:**
   ```bash
   # Domain: Pure logic, no mocks
   pytest tests/unit/core/domain/test_new_entity.py
   
   # Application: Mock all adapters
   pytest tests/unit/core/application/test_new_service.py
   
   # Integration: Real implementations
   pytest tests/integration/test_new_workflow.py
   ```

### Code Quality Checks

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy app/

# Run all checks
black app/ tests/ && ruff check app/ tests/ && mypy app/ && pytest
```

## Dependency Management

### Adding Dependencies

```bash
# Add production dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Add with version constraint
uv add "fastapi>=0.109.0,<0.110.0"
```

This automatically updates `pyproject.toml` and installs the package.

### Updating Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv pip install --upgrade <package-name>
uv pip freeze > requirements.txt  # if using requirements.txt
```

### Removing Dependencies

```bash
# Remove package
uv pip uninstall <package-name>

# Then remove from pyproject.toml manually
uv sync
```

## Architecture Reminders

### Domain Layer (`app/core/domain/`)
- **Pure business logic**
- No I/O operations
- No framework dependencies
- Dataclasses or plain Python classes
- Easily testable in isolation

**Example:**
```python
# app/core/domain/entities/diagram.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Diagram:
    id: str
    content: bytes
    format: str
    created_at: datetime
    analyzed: bool = False
```

### Application Layer (`app/core/application/`)
- **Use case orchestration**
- Coordinates domain + adapters
- Defines ports (interfaces)
- Transaction boundaries
- Domain exceptions

**Example:**
```python
# app/core/application/services/diagram_service.py
class DiagramService:
    def __init__(self, repository, event_publisher):
        self.repository = repository
        self.event_publisher = event_publisher
    
    async def upload_diagram(self, content: bytes, format: str) -> Diagram:
        # Create domain entity
        diagram = Diagram(id=generate_id(), content=content, format=format, ...)
        # Save via adapter
        await self.repository.save(diagram)
        # Publish event via adapter
        await self.event_publisher.publish("diagram.uploaded", {...})
        return diagram
```

### Adapter Layer (`app/adapter/`)

**Driver** (inbound - receive requests):
```python
# app/adapter/driver/event_listeners/sqs_handler.py
async def handle_diagram_upload(message: dict):
    # Parse message
    # Delegate to application service
    service = get_diagram_service()
    await service.process_upload(message['diagram_id'])
```

**Driven** (outbound - external interactions):
```python
# app/adapter/driven/persistence/file_repository.py
class FileRepository:
    async def save(self, diagram: Diagram) -> None:
        # Save to filesystem/S3/database
        pass
```

## Troubleshooting

### Common Issues

**Import errors when running:**
```bash
# Solution: Ensure virtual environment is activated
# Windows
.venv\Scripts\Activate.ps1

# Verify
python -c "import sys; print(sys.prefix)"
# Should show .venv path
```

**Module not found:**
```bash
# Solution: Reinstall dependencies
uv sync

# Or specific package
uv add <package-name>
```

**Tests failing:**
```bash
# Check test structure mirrors app structure
# tests/unit/core/application/ mirrors app/core/application/

# Verify mocks are properly configured
# Use AsyncMock for async functions

# Check fixtures are defined
# In conftest.py or same test file
```

**Architecture violations:**
```bash
# Check: Domain layer has no infrastructure imports
# Verify: Adapters implement ports from application layer
# Ensure: Dependencies flow inward (Adapters → App → Domain)
```

**Port already in use:**
```bash
# Find and kill process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Unix/macOS
lsof -ti:8000 | xargs kill -9
```

**Coverage not showing all files:**
```bash
# Ensure __init__.py exists in all directories
# Run with explicit source
pytest --cov=app --cov-report=term-missing tests/
```

## Useful Development Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Install with dev tools | `uv sync --extra dev` |
| Run service | `python main.py` |
| Run all tests | `pytest` |
| Run unit tests | `pytest tests/unit/` |
| Run integration tests | `pytest tests/integration/` |
| Run with coverage | `pytest --cov=app --cov-report=html` |
| Run specific test | `pytest tests/path/to/test.py::test_name` |
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --dev <package>` |
| Update dependencies | `uv sync --upgrade` |
| Format code | `black app/ tests/` |
| Lint code | `ruff check app/ tests/` |
| Type check | `mypy app/` |
| List packages | `uv pip list` |
| Show package info | `uv pip show <package>` |

## Related Skills

When developing features, use these skills:

- **unit-test** - Write isolated tests for each layer
- **integration-test** - Test multi-layer workflows
- For architecture questions, refer to [architecture.instructions.md](../instructions/architecture.instructions.md)
