from uuid import UUID


class DiagramUpload:
    def __init__(
        self,
        diagram_upload_id: str | UUID,
        folder: str,
        extension: str = ".pdf",
    ):
        if not folder or not str(folder).strip():
            raise ValueError("folder must be a non-empty string")
        try:
            self.diagram_upload_id = UUID(str(diagram_upload_id))
        except Exception as exc:
            raise ValueError("diagram_upload_id must be a valid UUID") from exc
        
        if not extension or not str(extension).strip():
            raise ValueError("extension must be a non-empty string")
        if not str(extension).startswith("."):
            raise ValueError("extension must start with a dot (e.g., '.pdf')")
        
        self.folder = str(folder)
        self.extension = str(extension)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"DiagramUpload({self.diagram_upload_id!s}, "
            f"folder={self.folder!r}, extension={self.extension!r})"
        )
