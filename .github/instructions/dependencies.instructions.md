---
description: Managing dependencies with uv for the diagram analyzer service
applyTo: 'pyproject.toml'
---

# Dependencies

## Adding Dependencies

Add to `pyproject.toml` under `[project.dependencies]`, then sync:

```bash
# Add a dependency
uv add <package-name>

# Or edit pyproject.toml manually, then:
uv sync
```

## Project Library Choices

### Core Framework
```toml
"fastapi>=0.109.0",        # Async web framework
"uvicorn[standard]>=0.27.0",  # ASGI server
"pydantic>=2.6.0",         # Data validation (adapters only)
```

### Image Processing
```toml
"pdf2image>=10.2.0",          # Image manipulation
"opencv-python>=4.9.0",    # Computer vision
```

### ML & Object Detection
```toml
"ultralytics>=8.1.0",      # YOLO object detection
"torch>=2.2.0",            # PyTorch
"transformers>=4.37.0",    # Hugging Face models
```

### AWS Services
```toml
"boto3>=1.34.0",           # AWS SDK (S3, SQS, Textract)
```

**Primary AWS services:**
- **S3:** Diagram storage
- **Textract:** OCR and document analysis
- **SQS:** Event-driven processing
- **Lambda:** Serverless analysis

### Logging & HTTP
```toml
"structlog>=24.1.0",       # Structured JSON logging
"httpx>=0.26.0",           # Modern async HTTP client
```

### Utilities
```toml
"python-dotenv>=1.0.0",    # Environment variables
```

## Development Dependencies

```bash
# Install dev dependencies
uv sync --extra dev
```

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "behave>=1.2.6",
    "testcontainers[localstack]>=3.7.0",
    "black>=24.1.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]
```

## Version Pinning Strategy

- **Pin major/minor:** `>=X.Y.0` allows patch updates
- **Avoid exact pins:** Unless required for compatibility
- **Review before updates:** Run full test suite after dependency updates

## Useful Commands

```bash
# List installed packages
uv pip list

# Show package details
uv pip show <package-name>

# Update all dependencies
uv sync --upgrade
```
