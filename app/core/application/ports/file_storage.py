from typing import Protocol


class FileStorage(Protocol):
    """Port for file storage operations (driven adapter interface)."""

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from storage.

        Args:
            file_url: Direct HTTP(S) URL pointing to a diagram file.

        Returns:
            The file content as bytes

        Raises:
            FileNotFoundError: If the file does not exist
            FileStorageError: If the download operation fails
        """
        ...
