from typing import Protocol


class FileStorage(Protocol):
    """Port for file storage operations (driven adapter interface)."""

    async def download_file(self, folder: str, filename: str, extension: str) -> bytes:
        """Download a file from storage.

        Args:
            folder: The folder/prefix where the file is stored
            filename: The base filename (without extension)
            extension: The file extension (including the dot, e.g., '.pdf')

        Returns:
            The file content as bytes

        Raises:
            FileNotFoundError: If the file does not exist
            FileStorageError: If the download operation fails
        """
        ...
