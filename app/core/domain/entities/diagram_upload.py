from uuid import UUID


class DiagramUpload:
    def __init__(self, diagram_upload_id: str | UUID, folder: str):
        if not folder or not str(folder).strip():
            raise ValueError("folder must be a non-empty string")
        try:
            self.diagram_upload_id = UUID(str(diagram_upload_id))
        except Exception as exc:
            raise ValueError("diagram_upload_id must be a valid UUID") from exc
        self.folder = str(folder)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"DiagramUpload({self.diagram_upload_id!s}, folder={self.folder!r})"
