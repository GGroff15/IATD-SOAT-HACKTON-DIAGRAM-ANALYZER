from uuid import UUID


class DiagramUpload:
    def __init__(
        self,
        diagram_upload_id: str | UUID,
        folder: str | None = None,
        extension: str = ".pdf",
        file_url: str | None = None,
    ):
        normalized_folder = str(folder).strip() if folder is not None else ""
        normalized_file_url = str(file_url).strip() if file_url is not None else ""

        if not normalized_folder and not normalized_file_url:
            raise ValueError("either folder or file_url must be provided")

        try:
            self.diagram_upload_id = UUID(str(diagram_upload_id))
        except Exception as exc:
            raise ValueError("diagram_upload_id must be a valid UUID") from exc

        if not extension or not str(extension).strip():
            raise ValueError("extension must be a non-empty string")
        if not str(extension).startswith("."):
            raise ValueError("extension must start with a dot (e.g., '.pdf')")

        self.folder = normalized_folder if normalized_folder else None
        self.extension = str(extension)
        self.file_url = normalized_file_url if normalized_file_url else None

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"DiagramUpload({self.diagram_upload_id!s}, "
            f"folder={self.folder!r}, file_url={self.file_url!r}, extension={self.extension!r})"
        )
