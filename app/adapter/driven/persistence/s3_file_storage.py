import structlog
from botocore.exceptions import ClientError

from app.core.application.exceptions import FileNotFoundError, FileStorageError

logger = structlog.get_logger()


class S3FileStorage:
    """S3 implementation of FileStorage port for downloading diagram files."""

    def __init__(self, s3_client, bucket_name: str):
        """Initialize S3 file storage adapter.

        Args:
            s3_client: Boto3 S3 client instance
            bucket_name: Name of the S3 bucket to use
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from S3 storage.

        Args:
            file_url: Direct S3 URI locator in s3://bucket/key format

        Returns:
            The file content as bytes

        Raises:
            FileNotFoundError: If the file does not exist in S3
            FileStorageError: If the download operation fails
        """
        bucket, key = self._resolve_from_file_url(file_url)
        
        logger.info(
            "s3.download_file.start",
            bucket=bucket,
            key=key,
            file_url=file_url,
        )
        
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read()
            
            logger.info(
                "s3.download_file.success",
                bucket=bucket,
                key=key,
                size_bytes=len(content),
            )
            
            return content
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            
            if error_code == "NoSuchKey":
                logger.warning(
                    "s3.download_file.not_found",
                    bucket=bucket,
                    key=key,
                )
                raise FileNotFoundError(
                    f"File {key} not found in bucket {bucket}"
                ) from e
            
            logger.error(
                "s3.download_file.client_error",
                bucket=bucket,
                key=key,
                error_code=error_code,
                error=str(e),
            )
            raise FileStorageError(
                f"Failed to download file {key} from S3: {error_code}"
            ) from e
            
        except Exception as e:
            logger.error(
                "s3.download_file.unexpected_error",
                bucket=bucket,
                key=key,
                error=str(e),
            )
            raise FileStorageError(
                f"Unexpected error during file download: {str(e)}"
            ) from e

    def _resolve_from_file_url(self, file_url: str) -> tuple[str, str]:
        normalized_file_url = file_url.strip()
        if not normalized_file_url.startswith("s3://"):
            raise FileStorageError("Only s3:// URIs are supported for file download")

        uri_without_scheme = normalized_file_url[len("s3://") :]
        parts = uri_without_scheme.split("/", 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise FileStorageError("S3 URI must include bucket and object key")

        return parts[0], parts[1]
