# Diagram Analyzer Service

Python 3.12 FastAPI microservice that analyzes architecture diagrams using a hexagonal architecture. The service receives an HTTP request with a diagram file URL, downloads the file, converts it to an image, detects diagram components and connections, extracts text with OCR, builds a graph, validates architectural rules, optionally enriches the analysis with an OpenAI-compatible LLM, and publishes the result or error to RabbitMQ.

## What It Does

The processing pipeline is:

1. Accepts a processing request through `POST /analyze`.
2. Downloads the diagram from an HTTP(S) URL.
3. Converts supported PDFs and images to normalized PNG bytes.
4. Sends the image to an external YOLO inference API for component and connection detection.
5. Runs PaddleOCR over detected component regions.
6. Builds an architecture graph and validates architectural rules.
7. Optionally calls an OpenAI-compatible chat completions API for additional analysis.
8. Publishes analysis results or error reports to RabbitMQ.

The service does not host YOLO inference or RabbitMQ internally. They must be available through configuration.

## Prerequisites

- Python 3.12.
- [uv](https://github.com/astral-sh/uv) for dependency management.
- Docker and Docker Compose, if running in containers.
- External YOLO inference API that accepts `POST /infer` multipart uploads.
- RabbitMQ reachable by the service.
- HTTP(S)-reachable input files.
- Optional OpenAI-compatible chat completions endpoint for LLM analysis.

For PDF processing, the application uses `pdf2image`. The Docker image includes runtime packages needed by the application, but local execution may require Poppler to be installed on your machine.

## Local Setup

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd diagram-analyzer-service
uv sync --extra dev
```

Create a local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with the endpoints for your external dependencies. At minimum, set values that allow the service to reach:

- `YOLO_INFERENCE_BASE_URL`
- `RABBITMQ_HOST`
- `RABBITMQ_PORT`

Start the API:

```bash
uv run python main.py
```

For development with reload:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is exposed at:

- Base URL: `http://localhost:8000`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Processing endpoint: `POST /analyze`

## Run With Docker

Build the image:

```bash
docker build -t diagram-analyzer-service:latest .
```

Create a Docker environment file:

```bash
cp .docker.env.example .docker.env
```

On Windows PowerShell:

```powershell
Copy-Item .docker.env.example .docker.env
```

Edit `.docker.env` for container networking. For dependencies running on the host machine, `host.docker.internal` is usually the right hostname on Docker Desktop.

Run the container:

```bash
docker run --rm --env-file .docker.env -p 8000:8000 diagram-analyzer-service:latest
```

The image starts the application with:

```bash
/app/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Run With Docker Compose

Docker Compose starts:

- `diagram-analyzer-service`
- `mistral`, an Ollama container exposed on port `1234`
- `mistral-pull`, a one-shot container that pulls the configured Mistral model into the shared Ollama volume

RabbitMQ, the YOLO inference API, and the OpenTelemetry collector are not defined by this Compose file. They must already be reachable from the `soat-net` Docker network or from the configured hostnames.

Create the external network if it does not exist:

```bash
docker network create soat-net
```

Create the Compose environment file:

```bash
cp .docker.env.example .docker.env
```

On Windows PowerShell:

```powershell
Copy-Item .docker.env.example .docker.env
```

Edit `.docker.env` so the container can reach its dependencies. Important values usually include:

- `YOLO_INFERENCE_BASE_URL`
- `RABBITMQ_HOST`
- `RABBITMQ_PORT`
- `OPENAI_BASE_URL`, if using the Compose Ollama service or another OpenAI-compatible endpoint

Start the stack:

```bash
docker compose up --build
```

The analyzer is exposed at:

- Base URL: `http://localhost:8000`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Processing endpoint: `POST /analyze`

## API Usage

### Start Analysis

- Method: `POST`
- Path: `/analyze`
- Success status: `202 Accepted`

Request body:

```json
{
  "protocol": "550e8400-e29b-41d4-a716-446655440000",
  "file": {
    "url": "https://example.com/uploads/project-a/diagram.pdf",
    "mimetype": "application/pdf"
  }
}
```

Response:

```json
{
  "status": "accepted",
  "protocol": "550e8400-e29b-41d4-a716-446655440000"
}
```

Request rules:

- `protocol` must be a valid UUID.
- `file.url` must be an `http://` or `https://` URL.
- The file extension is read from the URL when present.
- If the URL has no extension, the service can infer it from supported MIME types.
- Supported input formats are `.pdf`, `.png`, `.jpg`, and `.jpeg`.

The request returns once processing has been scheduled. Analysis continues asynchronously in the application process, and the final result or error is published to RabbitMQ.

## Configuration

The service uses environment variables loaded by `pydantic-settings`.

- Local Python execution loads `.env` from the repository root.
- Docker Compose loads `.docker.env`.
- Direct `docker run` should pass variables with `--env-file .docker.env` or individual `-e` options.

Do not commit real `.env` or `.docker.env` files.

| Group | Variable | Default | Purpose |
| --- | --- | --- | --- |
| API | `API_HOST` | `0.0.0.0` | Host used by `python main.py`. |
| API | `API_PORT` | `8000` | Port used by `python main.py`. |
| File download | `FILE_DOWNLOAD_TIMEOUT_SECONDS` | `30.0` | Timeout for downloading the input file. |
| YOLO inference | `YOLO_INFERENCE_BASE_URL` | `http://127.0.0.1:8000` | Base URL for the external YOLO inference service. |
| YOLO inference | `YOLO_INFERENCE_INFER_PATH` | `/infer` | Inference path appended to the base URL. |
| YOLO inference | `YOLO_INFERENCE_TIMEOUT_SECONDS` | `10.0` | Timeout for YOLO inference requests. |
| YOLO inference | `YOLO_CONNECTION_ARROW_LINE_CLASS` | `arrow_line` | Detection label used for connection lines. |
| YOLO inference | `YOLO_CONNECTION_ARROW_HEAD_CLASS` | `arrow_head` | Detection label used for arrow heads. |
| RabbitMQ | `RABBITMQ_HOST` | `localhost` | RabbitMQ host. |
| RabbitMQ | `RABBITMQ_PORT` | `5672` | RabbitMQ port. |
| RabbitMQ | `RABBITMQ_QUEUE_NAME` | `analysis_response` | Queue used for analysis results and error reports. |
| RabbitMQ | `RABBITMQ_MESSAGE_TTL_MS` | `5000` | Message TTL configured on the response queue. |
| RabbitMQ | `RABBITMQ_DLX_EXCHANGE_NAME` | `analysis_response_dlx_exchange` | Dead-letter exchange name. |
| RabbitMQ | `RABBITMQ_DLQ_QUEUE_NAME` | `analysis_response_dlq_queue` | Dead-letter queue name. |
| RabbitMQ | `RABBITMQ_DLQ_ROUTING_KEY` | `analysis_response_dlq_routing_key` | Dead-letter routing key. |
| LLM | `OPENAI_API_KEY` | empty | Enables LLM analysis when set. |
| LLM | `OPENAI_BASE_URL` | `https://api.openai.com` | OpenAI-compatible API base URL. |
| LLM | `OPENAI_CHAT_COMPLETIONS_PATH` | `/v1/chat/completions` | Chat completions path. |
| LLM | `OPENAI_MODEL` | `mistral-7b-instruct` | Model name sent to the chat completions endpoint. |
| LLM | `OPENAI_TIMEOUT_SECONDS` | `20.0` | LLM request timeout. |
| LLM | `OPENAI_TEMPERATURE` | `0.1` | LLM sampling temperature. |
| LLM | `OPENAI_MAX_TOKENS` | `900` | Maximum completion tokens. |
| PaddleOCR | `PADDLE_OCR_LANG` | `en` | OCR language. |
| PaddleOCR | `PADDLE_OCR_DEVICE` | `cpu` | OCR device. Use `gpu` to request GPU execution. |
| PaddleOCR | `PADDLE_OCR_USE_ANGLE_CLS` | `true` | Enables angle classification compatibility mode where supported. |
| PaddleOCR | `PADDLE_OCR_MODEL_DIR` | empty | Optional local OCR model directory. |
| PaddleOCR | `PADDLE_OCR_ENABLE_MKLDNN` | `false` | Enables MKL-DNN where supported. |
| OpenTelemetry | `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Enables OTLP tracing, metrics, and log export when set. |
| OpenTelemetry | `OTEL_EXPORTER_OTLP_PROTOCOL` | set by Compose | OTLP protocol used by the exporter. |
| OpenTelemetry | `OTEL_SERVICE_NAME` | set by Compose | Service name used in telemetry. |
| OpenTelemetry | `OTEL_RESOURCE_ATTRIBUTES` | set by Compose | Additional telemetry resource attributes. |
| OpenTelemetry | `OTEL_TRACES_EXPORTER` | set by Compose | Trace exporter selection. |
| OpenTelemetry | `OTEL_METRICS_EXPORTER` | set by Compose | Metrics exporter selection. |
| OpenTelemetry | `OTEL_LOGS_EXPORTER` | set by Compose | Logs exporter selection. |

## YOLO Inference Contract

The analyzer sends the converted diagram image to the configured inference endpoint as multipart form data:

- Method: `POST`
- Field name: `file`
- File name: `diagram.png`
- Content type: `image/png`

Expected response shape:

```json
{
  "detections": [
    {
      "label": "service",
      "bbox": {
        "x1": 10,
        "y1": 20,
        "x2": 110,
        "y2": 120
      }
    }
  ]
}
```

Each detection must include a non-empty `label` and a `bbox` object with numeric `x1`, `y1`, `x2`, and `y2` fields.

## RabbitMQ Output

The service declares the configured response queue and dead-letter topology before publishing.

Successful analysis messages are JSON objects with:

- `protocol`
- `components`
- `risks`
- `recommendations`

Error messages include:

- `protocol`
- `status`
- `reason`

RabbitMQ messages include correlation and tracing headers when available.

## Running Tests

Install development dependencies first:

```bash
uv sync --extra dev
```

Run all tests:

```bash
uv run pytest
```

Run unit tests:

```bash
uv run pytest tests/unit
```

Run integration tests:

```bash
uv run pytest tests/integration
```

Run tests with coverage:

```bash
uv run pytest --cov=app
```

Integration tests may require Docker because Testcontainers and LocalStack are used for some external-service scenarios.

## Development Notes

- The code is organized around hexagonal architecture:
  - `app/core/domain`: business entities.
  - `app/core/application`: use cases and ports.
  - `app/adapter/driver`: inbound adapters such as HTTP API handlers.
  - `app/adapter/driven`: outbound adapters such as RabbitMQ, OCR, conversion, YOLO, and LLM clients.
- The current HTTP ingress is `POST /analyze`.
- The input file source must be HTTP(S). `s3://` URLs are not accepted.
- LLM analysis is disabled unless `OPENAI_API_KEY` is set.
- Docker Compose uses the external Docker network `soat-net`.
- Docker Compose exposes the analyzer on host port `8000`.

## Troubleshooting

### `127.0.0.1` Works Locally But Fails In Docker

Inside a container, `127.0.0.1` points to the container itself. Use a service name on the Docker network or `host.docker.internal` when calling a dependency running on the host.

### RabbitMQ Publish Fails

Check `RABBITMQ_HOST`, `RABBITMQ_PORT`, and whether the broker is reachable from the service runtime. For Docker Compose, the broker must be attached to `soat-net` or exposed through a hostname the analyzer container can resolve.

### YOLO Inference Fails

Confirm that `YOLO_INFERENCE_BASE_URL` and `YOLO_INFERENCE_INFER_PATH` point to an endpoint that accepts multipart uploads with a `file` field and returns the expected `detections` JSON.

### PDF Conversion Fails Locally

Install Poppler for your operating system and make sure its binaries are available on `PATH`.

### LLM Analysis Is Missing

Set `OPENAI_API_KEY` to enable LLM analysis. Also confirm `OPENAI_BASE_URL`, `OPENAI_CHAT_COMPLETIONS_PATH`, and `OPENAI_MODEL` match your OpenAI-compatible server.
