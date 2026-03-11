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

    async def download_file(self, folder: str, filename: str, extension: str) -> bytes:
        """Download a file from S3 storage.

        Args:
            folder: The folder/prefix where the file is stored
            filename: The base filename (without extension)
            extension: The file extension (including the dot, e.g., '.pdf')

        Returns:
            The file content as bytes

        Raises:
            FileNotFoundError: If the file does not exist in S3
            FileStorageError: If the download operation fails
        """
        key = f"{folder}/{filename}{extension}"
        
        logger.info(
            "s3.download_file.start",
            bucket=self.bucket_name,
            key=key,
        )
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response["Body"].read()
            
            logger.info(
                "s3.download_file.success",
                bucket=self.bucket_name,
                key=key,
                size_bytes=len(content),
            )
            
            return content
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            
            if error_code == "NoSuchKey":
                logger.warning(
                    "s3.download_file.not_found",
                    bucket=self.bucket_name,
                    key=key,
                )
                raise FileNotFoundError(
                    f"File {key} not found in bucket {self.bucket_name}"
                ) from e
            
            logger.error(
                "s3.download_file.client_error",
                bucket=self.bucket_name,
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
                bucket=self.bucket_name,
                key=key,
                error=str(e),
            )
            raise FileStorageError(
                f"Unexpected error during file download: {str(e)}"
            ) from e
