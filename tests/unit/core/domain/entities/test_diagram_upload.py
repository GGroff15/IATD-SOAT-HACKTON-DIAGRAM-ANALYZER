from uuid import uuid4
import pytest

from app.core.domain.entities.diagram_upload import DiagramUpload


def test_diagram_upload_valid():
    uid = uuid4()
    d = DiagramUpload(uid, "some-folder")
    assert str(d.diagram_upload_id) == str(uid)
    assert d.folder == "some-folder"
    assert d.extension == ".pdf"  # default


def test_diagram_upload_with_custom_extension():
    uid = uuid4()
    d = DiagramUpload(uid, "some-folder", extension=".png")
    assert str(d.diagram_upload_id) == str(uid)
    assert d.folder == "some-folder"
    assert d.extension == ".png"


@pytest.mark.parametrize("folder", ["", "   ", None])
def test_diagram_upload_invalid_folder(folder):
    uid = uuid4()
    with pytest.raises(ValueError, match="folder must be a non-empty string"):
        DiagramUpload(uid, folder)


def test_diagram_upload_invalid_uuid():
    with pytest.raises(ValueError, match="diagram_upload_id must be a valid UUID"):
        DiagramUpload("not-a-uuid", "folder")


@pytest.mark.parametrize("extension", ["", "   ", None])
def test_diagram_upload_invalid_extension_empty(extension):
    uid = uuid4()
    with pytest.raises(ValueError, match="extension must be a non-empty string"):
        DiagramUpload(uid, "folder", extension=extension)


def test_diagram_upload_invalid_extension_no_dot():
    uid = uuid4()
    with pytest.raises(ValueError, match="extension must start with a dot"):
        DiagramUpload(uid, "folder", extension="pdf")
