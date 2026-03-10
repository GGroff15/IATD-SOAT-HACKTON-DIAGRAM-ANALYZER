---
description: Recommended libraries and how to add new dependencies to the project
applyTo: 'pyproject.toml'
---

# Dependencies

## Adding New Dependencies

1. Add to `pyproject.toml` under `[project.dependencies]`:

```toml
[project]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    # Add your dependency here
]
```

2. Reinstall the project:

```bash
uv sync
```

## Recommended Libraries by Category

### Web Framework

```toml
"fastapi>=0.109.0",        # Modern async web framework
"uvicorn[standard]>=0.27.0",  # ASGI server
"pydantic>=2.6.0",         # Data validation
"python-multipart",        # File upload support
```

**FastAPI** is recommended for:
- Built-in async support
- Automatic OpenAPI docs
- Type-based validation
- Modern Python features

### Image Processing

```toml
"pillow>=10.2.0",          # Image manipulation
"opencv-python>=4.9.0",    # Computer vision
```

**Use for:**
- Resizing and normalizing images
- Image enhancement
- Format conversion

### Object Detection & ML

```toml
"ultralytics>=8.1.0",      # YOLO object detection
"torch>=2.2.0",            # PyTorch for ML models
"transformers>=4.37.0",    # Hugging Face models
```

**Use for:**
- Detecting diagram components
- Custom model training
- Pre-trained models

### AWS Services

```toml
"boto3>=1.34.0",           # AWS SDK
"botocore>=1.34.0",        # AWS core functionality
```

**Services to use:**
- **S3:** Store uploaded diagrams
- **Textract:** OCR and document analysis
- **SQS:** Event-driven processing
- **Lambda:** Serverless analysis functions

### Testing

```toml
# Add to [project.optional-dependencies.dev]
"pytest>=8.0.0",
"pytest-asyncio>=0.23.0",   # Async test support
"pytest-cov>=4.1.0",        # Coverage reporting
"pytest-mock>=3.12.0",      # Mocking utilities
"httpx>=0.26.0",            # Async HTTP client for testing
"testcontainers[localstack]>=3.7.0",  # LocalStack for AWS testing
```

### Logging

```toml
"structlog>=24.1.0",       # Structured logging
```

**Structured logging** provides:
- JSON formatted logs
- Contextual information
- Better searchability

### HTTP Clients

```toml
"httpx>=0.26.0",           # Modern async HTTP client
# or
"requests>=2.31.0",        # Simple sync HTTP client
```

**Use httpx for:**
- Async HTTP calls
- Better connection pooling
- Modern API

### Utilities

```toml
"python-dotenv>=1.0.0",    # Environment variables
"pyyaml>=6.0.1",           # YAML parsing (for config)
```

## Development Dependencies

Add separately for development only:

```toml
[project.optional-dependencies]
dev = [
    "black>=24.1.0",       # Code formatter
    "ruff>=0.2.0",         # Fast linter
    "mypy>=1.8.0",         # Type checker
    "pre-commit>=3.6.0",   # Git hooks
]
```

Install with:
```bash
uv sync --extra dev
```

## Example Complete pyproject.toml

```toml
[project]
name = "diagram-analyzer-service"
version = "0.1.0"
description = "Microservice for analyzing diagrams"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
    "python-multipart",
    "pillow>=10.2.0",
    "opencv-python>=4.9.0",
    "ultralytics>=8.1.0",
    "boto3>=1.34.0",
    "structlog>=24.1.0",
    "httpx>=0.26.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "testcontainers[localstack]>=3.7.0",
    "black>=24.1.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Dependency Best Practices

- **Pin major versions:** Use `>=X.Y.0` to allow patch updates
- **Avoid version conflicts:** Check compatibility before adding
- **Keep minimal:** Only add what you actually use
- **Security:** Regularly update dependencies
- **Test after updates:** Run full test suite

## Checking Installed Packages

```bash
# List installed packages
uv pip list

# Show package info
uv pip show fastapi

# Check for outdated packages
uv pip list --outdated
```
