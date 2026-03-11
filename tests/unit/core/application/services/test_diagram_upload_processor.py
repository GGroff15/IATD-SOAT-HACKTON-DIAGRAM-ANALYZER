import asyncio
from uuid import uuid4

from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.application.services.diagram_upload_processor import process_diagram_upload


def test_process_diagram_upload_runs_without_error():
    upload = DiagramUpload(uuid4(), "folder-x")
    asyncio.run(process_diagram_upload(upload))
