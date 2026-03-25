## Diagram Analyzer Service

Python microservice for diagram analysis using hexagonal architecture.

## Run

1. Install dependencies:
	 - `uv sync`
2. Start service:
	 - `python main.py`

The service starts a FastAPI application and exposes the processing trigger endpoint.

## Processing Start Endpoint

- Method: `POST`
- Path: `/processing-start`

Request body:

```json
{
	"protocol": "PRT-2026-0001",
	"file": {
		"url": "s3://input-bucket/uploads/project-a/550e8400-e29b-41d4-a716-446655440000.pdf",
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
