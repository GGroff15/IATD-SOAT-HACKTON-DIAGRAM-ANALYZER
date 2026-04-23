from urllib.parse import urlsplit, urlunsplit

import httpx
import structlog

from app.core.application.exceptions import FileNotFoundError, FileStorageError

logger = structlog.get_logger()


class S3FileStorage:
    """HTTP-based implementation of FileStorage for bucket URLs."""

    def __init__(self, http_client: httpx.AsyncClient):
        """Initialize file storage adapter.

        Args:
            http_client: Async HTTP client for downloading files
        """
        self.http_client = http_client

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from an HTTP(S) URL.

        Args:
            file_url: HTTP(S) URL pointing to the diagram file

        Returns:
            The file content as bytes

        Raises:
            FileNotFoundError: If the file does not exist
            FileStorageError: If the download operation fails
        """
        normalized_file_url = file_url.strip()
        redacted_url = _redact_url(normalized_file_url)
        parsed = urlsplit(normalized_file_url)
        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            raise FileStorageError("Only http(s) URLs are supported for file download")

        if not parsed.netloc:
            raise FileStorageError("file_url must include a host")

        logger.info(
            "file.download.start",
            file_url=redacted_url,
        )

        try:
            response = await self.http_client.get(normalized_file_url)
        except httpx.RequestError as error:
            logger.error(
                "file.download.request_error",
                file_url=redacted_url,
                error=str(error),
            )
            raise FileStorageError(
                f"Failed to download file due to network error: {error}"
            ) from error

        if response.status_code == 404:
            logger.warning(
                "file.download.not_found",
                file_url=redacted_url,
                status_code=response.status_code,
            )
            raise FileNotFoundError(f"File not found at {redacted_url}")

        if response.status_code >= 400:
            logger.error(
                "file.download.http_error",
                file_url=redacted_url,
                status_code=response.status_code,
            )
            raise FileStorageError(
                f"Failed to download file: HTTP {response.status_code}"
            )

        content = response.content
        logger.info(
            "file.download.success",
            file_url=redacted_url,
            size_bytes=len(content),
        )
        return content


def _redact_url(file_url: str) -> str:
    parsed = urlsplit(file_url)
    if not parsed.query and not parsed.fragment:
        return file_url
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
