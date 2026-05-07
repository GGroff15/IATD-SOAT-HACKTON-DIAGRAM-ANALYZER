## Diagram Analyzer Service

Python microservice for diagram analysis using hexagonal architecture.

## Prerequisites

- **Python:** 3.12 or later
- **Package manager:** [uv](https://github.com/astral-sh/uv)
- **Container runtime (optional):** Docker
- **External service:** YOLO inference API (required for diagram detection)
- **Messaging broker:** RabbitMQ (required to publish results and errors)
- **HTTP file source:** Provide HTTP(S) URLs for input file access
- **LLM API:** OpenAI-compatible endpoint for enhanced analysis

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd diagram-analyzer-service
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Run Locally

1. Create your environment file from the template:
  ```bash
  cp .env.example .env
  ```

  On Windows PowerShell:
  ```powershell
  Copy-Item .env.example .env
  ```

2. Edit `.env` with the minimum required values:
  - `YOLO_INFERENCE_BASE_URL` (required in practice, default exists)
  - `RABBITMQ_HOST` (required in practice, default exists)

3. Start the service:
  ```bash
  python main.py
  ```

4. Verify the API is up:
  - Base URL: `http://localhost:8000`
  - Processing endpoint: `POST /processing-start`

## Run with Docker

1. Build the image:
  ```bash
  docker build -t diagram-analyzer-service:latest .
  ```

2. Run the container (replace placeholders):
  ```bash
  docker run --rm -p 8000:8000 \
    -e YOLO_INFERENCE_BASE_URL=http://host.docker.internal:8001 \
    -e RABBITMQ_HOST=host.docker.internal \
    -e RABBITMQ_PORT=5672 \
    -e RABBITMQ_QUEUE_NAME=analisys_response \
    diagram-analyzer-service:latest
  ```

3. Verify the API is up:
  - Base URL: `http://localhost:8000`
  - Processing endpoint: `POST /processing-start`

The image starts the app with:

```bash
/app/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Run with Docker Compose

1. Create the external network if it does not exist:
  ```bash
  docker network create soat-net
  ```

2. Edit `.docker.env` with your values (minimum required: `S3_BUCKET_NAME`).

3. Build and start the service:
  ```bash
  docker compose up --build
  ```

4. Verify the API is up:
  - Base URL: `http://localhost:8001`
  - Processing endpoint: `POST /processing-start`

## Configuration

Use `.env` in the project root. The `Settings` class loads this file automatically.

Tip: variables with defaults may still need overrides in Docker or multi-service environments.

### Minimum configuration to process requests

- `YOLO_INFERENCE_BASE_URL` (default: `http://127.0.0.1:8000`)
- `YOLO_INFERENCE_INFER_PATH` (default: `/infer`)
- `RABBITMQ_HOST` (default: `localhost`)
- `RABBITMQ_PORT` (default: `5672`)
- `RABBITMQ_QUEUE_NAME` (default: `analisys_response`)

### Optional and advanced configuration

API:

- `API_HOST` (default: `0.0.0.0`)
- `API_PORT` (default: `8000`)

File downloads:

- `FILE_DOWNLOAD_TIMEOUT_SECONDS` (default: `30.0`)

YOLO inference tuning:

- `YOLO_INFERENCE_TIMEOUT_SECONDS` (default: `10.0`)
- `YOLO_CONNECTION_ARROW_LINE_CLASS` (default: `arrow_line`)
- `YOLO_CONNECTION_ARROW_HEAD_CLASS` (default: `arrow_head`)

OpenAI-compatible LLM:

- `OPENAI_API_KEY` (empty disables LLM analysis)
- `OPENAI_BASE_URL` (default: `https://api.openai.com`)
- `OPENAI_CHAT_COMPLETIONS_PATH` (default: `/v1/chat/completions`)
- `OPENAI_MODEL` (default: `mistral-7b-instruct`)
- `OPENAI_TIMEOUT_SECONDS` (default: `20.0`)
- `OPENAI_TEMPERATURE` (default: `0.1`)
- `OPENAI_MAX_TOKENS` (default: `900`)

PaddleOCR:

- `PADDLE_OCR_LANG` (default: `en`)
- `PADDLE_OCR_DEVICE` (default: `cpu`)
- `PADDLE_OCR_USE_ANGLE_CLS` (default: `true`)
- `PADDLE_OCR_MODEL_DIR` (default: empty)
- `PADDLE_OCR_ENABLE_MKLDNN` (default: `false`)

See `.env.example` for a ready-to-copy baseline.

## Running Tests

Run all tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=app
```

Run specific test types:
```bash
# Unit tests only
pytest tests/unit

# Integration tests only
pytest tests/integration
```

## External YOLO Inference Dependency

Diagram detection now uses an external YOLO inference API instead of an embedded model runtime.

The analyzer sends each converted image to the configured `POST /infer` endpoint as multipart form data (`file` field) and expects:

```json
{
  "detections": [
    {
      "label": "service",
      "bbox": { "x1": 10, "y1": 20, "x2": 110, "y2": 120 }
    }
  ]
}
```

## Common Pitfalls

- `YOLO_INFERENCE_BASE_URL=http://127.0.0.1:8000` works for local single-machine setups, but usually fails in Docker unless that endpoint exists inside the same container.
- `RABBITMQ_HOST=localhost` in Docker points to the container itself, not your host machine or another service.
- This service does not run YOLO internally; you must provide an external YOLO inference API.
- `file.url` must be an HTTP(S) URL; `s3://` URLs are not supported.

## Processing Start Endpoint

- Method: `POST`
- Path: `/processing-start`

Request body:

```json
{
	"protocol": "PRT-2026-0001",
	"file": {
    "url": "https://example-bucket.s3.amazonaws.com/uploads/project-a/550e8400-e29b-41d4-a716-446655440000.pdf",
		"mimetype": "application/pdf"
	}
}
```

Response (`202 Accepted`):

```json
{
	"status": "accepted",
	"protocol": "PRT-2026-0001"
}
```

## Migration Notes

- Legacy SQS listener ingress has been removed.
- Upstream services must call `POST /processing-start` to trigger diagram processing.
- `protocol` is used as the processing identifier and must match UUID format expected by current domain model.
- Text extraction runs locally through PaddleOCR (default language: English).
