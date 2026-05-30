from offline_npu_renamer.core.models import FileKind
from offline_npu_renamer.core.scanner import classify_path, scan_folder


def test_classify_supported_documents_and_images():
    assert classify_path("notes.md") is FileKind.DOCUMENT
    assert classify_path("scan.PDF") is FileKind.DOCUMENT
    assert classify_path("photo.JPG") is FileKind.IMAGE
    assert classify_path("movie.mp4") is FileKind.UNSUPPORTED


def test_scan_folder_is_non_recursive_by_default(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "b.png").write_bytes(b"not a real png")
    (tmp_path / "c.mp4").write_bytes(b"video")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "d.txt").write_text("nested", encoding="utf-8")

    found = scan_folder(tmp_path)

    assert [item.path.name for item in found] == ["a.txt", "b.png"]
    assert [item.kind for item in found] == [FileKind.DOCUMENT, FileKind.IMAGE]
