from uuid import uuid4
import pytest

from app.core.domain.entities.diagram_upload import DiagramUpload


def test_diagram_upload_valid():
    uid = uuid4()
    d = DiagramUpload(uid, "some-folder")
    assert str(d.diagram_upload_id) == str(uid)
    assert d.folder == "some-folder"


@pytest.mark.parametrize("folder", ["", "   ", None])
def test_diagram_upload_invalid_folder(folder):
    uid = uuid4()
    with pytest.raises(ValueError):
        DiagramUpload(uid, folder)


def test_diagram_upload_invalid_uuid():
    with pytest.raises(ValueError):
        DiagramUpload("not-a-uuid", "folder")
