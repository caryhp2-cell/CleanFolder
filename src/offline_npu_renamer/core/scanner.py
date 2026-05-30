from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offline_npu_renamer.core.models import FileKind

DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif"}


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    kind: FileKind


def classify_path(path: str | Path) -> FileKind:
    suffix = Path(path).suffix.lower()
    if suffix in DOCUMENT_EXTENSIONS:
        return FileKind.DOCUMENT
    if suffix in IMAGE_EXTENSIONS:
        return FileKind.IMAGE
    return FileKind.UNSUPPORTED


def scan_folder(folder: str | Path) -> list[ScannedFile]:
    root = Path(folder)
    scanned: list[ScannedFile] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_file():
            continue
        kind = classify_path(child)
        if kind is not FileKind.UNSUPPORTED:
            scanned.append(ScannedFile(path=child, kind=kind))
    return scanned
