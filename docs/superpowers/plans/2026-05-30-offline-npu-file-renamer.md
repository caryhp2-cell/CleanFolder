# Offline NPU File Renamer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows offline desktop app that scans a selected folder, previews content-based filename suggestions with `YYYY-MM-DD_` prefixes, confirms batch renames, and writes undoable logs while requiring NPU-backed AI inference availability.

**Architecture:** Use a small Python package with separated core services for bundled model validation, NPU detection, file scanning, content extraction, filename generation, rename planning, and undo logging. The GUI is a thin PySide6 shell over the core services, so most behavior is testable without a desktop session.

**Tech Stack:** Python 3.11+, PySide6, pytest, pypdf, python-docx, Pillow, ONNX Runtime, JSON Lines logs.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, dev dependencies, pytest config, console script.
- `README.md`: local setup, offline model placement, NPU behavior, run commands.
- `src/offline_npu_renamer/__init__.py`: package marker and version.
- `src/offline_npu_renamer/app.py`: PySide6 application entrypoint.
- `src/offline_npu_renamer/core/models.py`: shared dataclasses and enums.
- `src/offline_npu_renamer/core/model_assets.py`: bundled model manifest loading, SHA-256 validation, and model availability reporting.
- `src/offline_npu_renamer/core/npu.py`: ONNX Runtime provider detection and NPU availability policy.
- `src/offline_npu_renamer/core/scanner.py`: supported file discovery in one selected folder.
- `src/offline_npu_renamer/core/extractors.py`: local document and image text extraction.
- `src/offline_npu_renamer/core/filenames.py`: date selection, title cleanup, collision-safe target generation.
- `src/offline_npu_renamer/core/analyzer.py`: analyzer orchestration that converts files into rename suggestions.
- `src/offline_npu_renamer/core/renamer.py`: apply rename plans and skip unsafe operations.
- `src/offline_npu_renamer/core/logging.py`: JSON Lines rename log and undo records.
- `src/offline_npu_renamer/ui/main_window.py`: folder picker, NPU status, preview table, apply and undo buttons.
- `models/manifest.json`: required bundled offline model manifest.
- `models/document-title-v1.onnx`: bundled document title or summarization model asset, stored directly or via Git LFS.
- `models/image-title-v1.onnx`: bundled OCR or image understanding model asset, stored directly or via Git LFS.
- `tests/fixtures/`: small text and generated binary fixtures.
- `tests/test_*.py`: focused tests for each core service.

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/offline_npu_renamer/__init__.py`
- Create: `src/offline_npu_renamer/core/__init__.py`
- Create: `src/offline_npu_renamer/ui/__init__.py`

- [ ] **Step 1: Create package metadata**

Write `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "offline-npu-renamer"
version = "0.1.0"
description = "Offline Windows desktop app for NPU-gated content-based file renaming."
requires-python = ">=3.11"
dependencies = [
  "onnxruntime>=1.18",
  "pillow>=10.0",
  "pypdf>=4.0",
  "python-docx>=1.1",
  "PySide6>=6.7",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
offline-npu-renamer = "offline_npu_renamer.app:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Add package markers**

Write `src/offline_npu_renamer/__init__.py`:

```python
__version__ = "0.1.0"
```

Write empty files:

```text
src/offline_npu_renamer/core/__init__.py
src/offline_npu_renamer/ui/__init__.py
```

- [ ] **Step 3: Add README**

Write `README.md`:

```markdown
# Offline NPU Renamer

Windows desktop app for offline, content-based file rename suggestions.

The first version supports documents and images. AI inference is gated by bundled model validation and NPU availability. If bundled model files are missing, hashes do not match, or no supported NPU-backed ONNX Runtime provider is available, the app disables analysis instead of falling back to CPU or GPU inference.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
offline-npu-renamer
```

## Bundled offline model files

The first version ships with offline ONNX model files under `models/` and describes them in `models/manifest.json`. The app must not download models at runtime. If the installed model files are missing or corrupted, analysis is disabled.
```

- [ ] **Step 4: Verify install metadata**

Run: `python -m pip install -e ".[dev]"`

Expected: package installs successfully.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml README.md src/offline_npu_renamer
git commit -m "chore: scaffold offline NPU renamer project"
```

## Task 2: Shared Core Models

**Files:**
- Create: `src/offline_npu_renamer/core/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write model tests**

Write `tests/test_models.py`:

```python
from pathlib import Path

from offline_npu_renamer.core.models import DateSource, FileKind, RenameSuggestion


def test_rename_suggestion_keeps_paths_and_metadata():
    suggestion = RenameSuggestion(
        source_path=Path("C:/demo/report.pdf"),
        target_path=Path("C:/demo/2026-05-30_report.pdf"),
        file_kind=FileKind.DOCUMENT,
        date_source=DateSource.CONTENT,
        confidence=0.82,
        reason="Detected title and content date.",
    )

    assert suggestion.source_path.name == "report.pdf"
    assert suggestion.target_path.name == "2026-05-30_report.pdf"
    assert suggestion.file_kind is FileKind.DOCUMENT
    assert suggestion.date_source is DateSource.CONTENT
```

- [ ] **Step 2: Run the failing test**

Run: `pytest tests/test_models.py -v`

Expected: FAIL because `offline_npu_renamer.core.models` does not exist.

- [ ] **Step 3: Implement shared models**

Write `src/offline_npu_renamer/core/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DateSource(str, Enum):
    CONTENT = "content"
    METADATA = "metadata"
    MODIFIED_TIME = "modified_time"
    CURRENT_DATE = "current_date"


class FileKind(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


class SuggestionStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NpuStatus:
    available: bool
    provider: str | None
    message: str
    available_providers: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    metadata_date: str | None
    analyzer_id: str


@dataclass(frozen=True)
class RenameSuggestion:
    source_path: Path
    target_path: Path
    file_kind: FileKind
    date_source: DateSource
    confidence: float
    reason: str
    status: SuggestionStatus = SuggestionStatus.READY
```

- [ ] **Step 4: Verify model tests pass**

Run: `pytest tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/models.py tests/test_models.py
git commit -m "feat: add shared rename models"
```

## Task 3: NPU Detection Policy

**Files:**
- Create: `src/offline_npu_renamer/core/npu.py`
- Test: `tests/test_npu.py`

- [ ] **Step 1: Write NPU policy tests**

Write `tests/test_npu.py`:

```python
from offline_npu_renamer.core.npu import detect_npu_status


def test_detect_npu_accepts_known_npu_provider():
    status = detect_npu_status(
        available_providers=("QNNExecutionProvider", "CPUExecutionProvider")
    )

    assert status.available is True
    assert status.provider == "QNNExecutionProvider"


def test_detect_npu_rejects_cpu_and_gpu_only():
    status = detect_npu_status(
        available_providers=("DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider")
    )

    assert status.available is False
    assert status.provider is None
    assert "No supported NPU" in status.message
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_npu.py -v`

Expected: FAIL because `detect_npu_status` does not exist.

- [ ] **Step 3: Implement NPU detection**

Write `src/offline_npu_renamer/core/npu.py`:

```python
from __future__ import annotations

from collections.abc import Sequence

from offline_npu_renamer.core.models import NpuStatus

SUPPORTED_NPU_PROVIDERS = (
    "QNNExecutionProvider",
    "OpenVINOExecutionProvider",
    "VitisAIExecutionProvider",
)


def get_onnxruntime_providers() -> tuple[str, ...]:
    import onnxruntime as ort

    return tuple(ort.get_available_providers())


def detect_npu_status(
    available_providers: Sequence[str] | None = None,
) -> NpuStatus:
    providers = tuple(available_providers or get_onnxruntime_providers())
    for provider in SUPPORTED_NPU_PROVIDERS:
        if provider in providers:
            return NpuStatus(
                available=True,
                provider=provider,
                message=f"NPU-backed provider available: {provider}",
                available_providers=providers,
            )

    return NpuStatus(
        available=False,
        provider=None,
        message=(
            "No supported NPU-backed ONNX Runtime provider was found. "
            "Analysis is disabled to avoid CPU/GPU AI fallback."
        ),
        available_providers=providers,
    )
```

- [ ] **Step 4: Verify NPU tests pass**

Run: `pytest tests/test_npu.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/npu.py tests/test_npu.py
git commit -m "feat: add NPU inference gate"
```

## Task 3A: Bundled Model Asset Validation

**Files:**
- Create: `src/offline_npu_renamer/core/model_assets.py`
- Test: `tests/test_model_assets.py`

- [ ] **Step 1: Write bundled model validation tests**

Write `tests/test_model_assets.py`:

```python
import hashlib
import json

from offline_npu_renamer.core.model_assets import validate_model_assets


def test_validate_model_assets_accepts_present_hashed_models(tmp_path):
    model_path = tmp_path / "document-title-v1.onnx"
    model_path.write_bytes(b"fake-onnx-bytes")
    digest = hashlib.sha256(b"fake-onnx-bytes").hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "document-title-v1",
                        "path": "document-title-v1.onnx",
                        "task": "document-title",
                        "sha256": digest,
                        "required_provider": "QNNExecutionProvider",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validate_model_assets(manifest_path)

    assert status.available is True
    assert status.message == "Bundled offline models validated."


def test_validate_model_assets_rejects_missing_model(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "image-title-v1",
                        "path": "image-title-v1.onnx",
                        "task": "image-title",
                        "sha256": "abc",
                        "required_provider": "QNNExecutionProvider",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validate_model_assets(manifest_path)

    assert status.available is False
    assert "Missing bundled model" in status.message
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_model_assets.py -v`

Expected: FAIL because `model_assets.py` does not exist.

- [ ] **Step 3: Implement bundled model validation**

Write `src/offline_npu_renamer/core/model_assets.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelAssetStatus:
    available: bool
    message: str
    model_ids: tuple[str, ...]


def validate_model_assets(manifest_path: Path) -> ModelAssetStatus:
    if not manifest_path.exists():
        return ModelAssetStatus(False, f"Missing bundled model manifest: {manifest_path}", ())

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    model_ids: list[str] = []

    for model in manifest.get("models", []):
        model_id = str(model["id"])
        model_ids.append(model_id)
        model_path = root / str(model["path"])
        if not model_path.exists():
            return ModelAssetStatus(False, f"Missing bundled model: {model_id}", tuple(model_ids))

        expected_hash = str(model["sha256"]).lower()
        actual_hash = _sha256(model_path)
        if actual_hash != expected_hash:
            return ModelAssetStatus(
                False,
                f"Bundled model hash mismatch for {model_id}",
                tuple(model_ids),
            )

    if not model_ids:
        return ModelAssetStatus(False, "Bundled model manifest contains no models.", ())

    return ModelAssetStatus(True, "Bundled offline models validated.", tuple(model_ids))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Verify bundled model validation tests pass**

Run: `pytest tests/test_model_assets.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/model_assets.py tests/test_model_assets.py
git commit -m "feat: validate bundled offline models"
```

## Task 4: File Scanner

**Files:**
- Create: `src/offline_npu_renamer/core/scanner.py`
- Test: `tests/test_scanner.py`

- [ ] **Step 1: Write scanner tests**

Write `tests/test_scanner.py`:

```python
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
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_scanner.py -v`

Expected: FAIL because scanner functions do not exist.

- [ ] **Step 3: Implement scanner**

Write `src/offline_npu_renamer/core/scanner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offline_npu_renamer.core.models import FileKind

DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff"}


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
```

- [ ] **Step 4: Verify scanner tests pass**

Run: `pytest tests/test_scanner.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/scanner.py tests/test_scanner.py
git commit -m "feat: scan supported documents and images"
```

## Task 5: Filename Generation

**Files:**
- Create: `src/offline_npu_renamer/core/filenames.py`
- Test: `tests/test_filenames.py`

- [ ] **Step 1: Write filename tests**

Write `tests/test_filenames.py`:

```python
from datetime import date

from offline_npu_renamer.core.filenames import build_target_path, clean_title, choose_date
from offline_npu_renamer.core.models import DateSource


def test_clean_title_removes_invalid_windows_characters():
    assert clean_title("Invoice: ACME / May*Payment?") == "invoice_acme_may_payment"


def test_choose_date_uses_content_before_metadata_and_modified():
    chosen = choose_date(
        content_dates=["2026-05-30"],
        metadata_date="2026-04-01",
        modified_date=date(2026, 3, 2),
        today=date(2026, 1, 1),
    )

    assert chosen.value == "2026-05-30"
    assert chosen.source is DateSource.CONTENT


def test_build_target_path_adds_suffix_for_collisions(tmp_path):
    source = tmp_path / "old.pdf"
    source.write_text("x", encoding="utf-8")
    (tmp_path / "2026-05-30_invoice.pdf").write_text("existing", encoding="utf-8")

    target = build_target_path(source, "2026-05-30", "Invoice")

    assert target.name == "2026-05-30_invoice-2.pdf"
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_filenames.py -v`

Expected: FAIL because filename helpers do not exist.

- [ ] **Step 3: Implement filename helpers**

Write `src/offline_npu_renamer/core/filenames.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from offline_npu_renamer.core.models import DateSource

INVALID_WINDOWS_CHARS = r'<>:"/\\|?*'
DATE_PATTERN = re.compile(r"\b(20\d{2})[-_/\.](0[1-9]|1[0-2])[-_/\.](0[1-9]|[12]\d|3[01])\b")


@dataclass(frozen=True)
class ChosenDate:
    value: str
    source: DateSource


def clean_title(title: str, max_length: int = 80) -> str:
    cleaned = title.lower()
    for char in INVALID_WINDOWS_CHARS:
        cleaned = cleaned.replace(char, " ")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_length].rstrip("_")


def find_content_dates(text: str) -> list[str]:
    return [f"{year}-{month}-{day}" for year, month, day in DATE_PATTERN.findall(text)]


def choose_date(
    content_dates: list[str],
    metadata_date: str | None,
    modified_date: date,
    today: date,
) -> ChosenDate:
    if content_dates:
        return ChosenDate(content_dates[0], DateSource.CONTENT)
    if metadata_date:
        return ChosenDate(metadata_date, DateSource.METADATA)
    if modified_date:
        return ChosenDate(modified_date.isoformat(), DateSource.MODIFIED_TIME)
    return ChosenDate(today.isoformat(), DateSource.CURRENT_DATE)


def build_target_path(source_path: Path, date_prefix: str, title: str) -> Path:
    folder = source_path.parent
    stem = f"{date_prefix}_{clean_title(title)}"
    suffix = source_path.suffix.lower()
    candidate = folder / f"{stem}{suffix}"
    counter = 2
    while candidate.exists() and candidate.resolve() != source_path.resolve():
        candidate = folder / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate
```

- [ ] **Step 4: Verify filename tests pass**

Run: `pytest tests/test_filenames.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/filenames.py tests/test_filenames.py
git commit -m "feat: generate safe dated filenames"
```

## Task 6: Local Content Extractors

**Files:**
- Create: `src/offline_npu_renamer/core/extractors.py`
- Test: `tests/test_extractors.py`

- [ ] **Step 1: Write extractor tests**

Write `tests/test_extractors.py`:

```python
from offline_npu_renamer.core.extractors import extract_document_content, extract_image_content


def test_extract_text_document(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Project Review 2026-05-30\nImportant notes.", encoding="utf-8")

    content = extract_document_content(path)

    assert "Project Review" in content.text
    assert content.analyzer_id == "text-direct"


def test_extract_markdown_document(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Meeting Notes\nDate: 2026-05-30", encoding="utf-8")

    content = extract_document_content(path)

    assert "Meeting Notes" in content.text


def test_extract_image_returns_metadata_without_ocr_for_first_version(tmp_path):
    from PIL import Image

    path = tmp_path / "diagram.png"
    Image.new("RGB", (8, 8), color="white").save(path)

    content = extract_image_content(path)

    assert "diagram" in content.text
    assert content.analyzer_id == "image-metadata"
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_extractors.py -v`

Expected: FAIL because extractor functions do not exist.

- [ ] **Step 3: Implement local extractors**

Write `src/offline_npu_renamer/core/extractors.py`:

```python
from __future__ import annotations

from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader

from offline_npu_renamer.core.models import ExtractedContent


def extract_document_content(path: Path) -> ExtractedContent:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return ExtractedContent(
            text=path.read_text(encoding="utf-8", errors="replace"),
            metadata_date=None,
            analyzer_id="text-direct",
        )
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        metadata_date = _normalize_pdf_date(getattr(reader.metadata, "creation_date", None))
        return ExtractedContent(text=text, metadata_date=metadata_date, analyzer_id="pdf-text")
    if suffix == ".docx":
        document = Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return ExtractedContent(text=text, metadata_date=None, analyzer_id="docx-text")
    raise ValueError(f"Unsupported document type: {path.suffix}")


def extract_image_content(path: Path) -> ExtractedContent:
    with Image.open(path) as image:
        width, height = image.size
    text = f"{path.stem.replace('_', ' ')} image {width}x{height}"
    return ExtractedContent(text=text, metadata_date=None, analyzer_id="image-metadata")


def _normalize_pdf_date(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return None
```

- [ ] **Step 4: Verify extractor tests pass**

Run: `pytest tests/test_extractors.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/extractors.py tests/test_extractors.py
git commit -m "feat: extract local document and image content"
```

## Task 7: Analyzer Orchestration

**Files:**
- Create: `src/offline_npu_renamer/core/analyzer.py`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write analyzer tests**

Write `tests/test_analyzer.py`:

```python
from datetime import date

from offline_npu_renamer.core.analyzer import analyze_file
from offline_npu_renamer.core.models import DateSource, FileKind, NpuStatus


def test_analyze_file_requires_npu(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Meeting Notes 2026-05-30", encoding="utf-8")

    suggestion = analyze_file(
        path=path,
        file_kind=FileKind.DOCUMENT,
        npu_status=NpuStatus(False, None, "No supported NPU", ("CPUExecutionProvider",)),
        today=date(2026, 5, 30),
    )

    assert suggestion.status.value == "error"
    assert suggestion.target_path == path
    assert "NPU" in suggestion.reason


def test_analyze_text_file_generates_content_date_name_when_npu_available(tmp_path):
    path = tmp_path / "old.txt"
    path.write_text("Quarterly Planning 2026-05-30\nRoadmap review", encoding="utf-8")

    suggestion = analyze_file(
        path=path,
        file_kind=FileKind.DOCUMENT,
        npu_status=NpuStatus(True, "QNNExecutionProvider", "ok", ("QNNExecutionProvider",)),
        today=date(2026, 1, 1),
    )

    assert suggestion.status.value == "ready"
    assert suggestion.target_path.name == "2026-05-30_quarterly_planning.txt"
    assert suggestion.date_source is DateSource.CONTENT
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_analyzer.py -v`

Expected: FAIL because analyzer does not exist.

- [ ] **Step 3: Implement analyzer**

Write `src/offline_npu_renamer/core/analyzer.py`:

```python
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from offline_npu_renamer.core.extractors import extract_document_content, extract_image_content
from offline_npu_renamer.core.filenames import build_target_path, choose_date, find_content_dates
from offline_npu_renamer.core.models import (
    DateSource,
    FileKind,
    NpuStatus,
    RenameSuggestion,
    SuggestionStatus,
)


def analyze_file(
    path: Path,
    file_kind: FileKind,
    npu_status: NpuStatus,
    today: date | None = None,
) -> RenameSuggestion:
    if not npu_status.available:
        return RenameSuggestion(
            source_path=path,
            target_path=path,
            file_kind=file_kind,
            date_source=DateSource.CURRENT_DATE,
            confidence=0.0,
            reason=npu_status.message,
            status=SuggestionStatus.ERROR,
        )

    current_date = today or date.today()
    content = (
        extract_document_content(path)
        if file_kind is FileKind.DOCUMENT
        else extract_image_content(path)
    )
    title = _first_meaningful_line(content.text) or path.stem
    modified_date = datetime.fromtimestamp(path.stat().st_mtime).date()
    chosen_date = choose_date(
        content_dates=find_content_dates(content.text),
        metadata_date=content.metadata_date,
        modified_date=modified_date,
        today=current_date,
    )
    target = build_target_path(path, chosen_date.value, title)
    confidence = 0.75 if chosen_date.source is DateSource.CONTENT else 0.55
    return RenameSuggestion(
        source_path=path,
        target_path=target,
        file_kind=file_kind,
        date_source=chosen_date.source,
        confidence=confidence,
        reason=f"{content.analyzer_id} generated title from local content.",
        status=SuggestionStatus.READY,
    )


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return ""
```

- [ ] **Step 4: Verify analyzer tests pass**

Run: `pytest tests/test_analyzer.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/analyzer.py tests/test_analyzer.py
git commit -m "feat: analyze files into rename suggestions"
```

## Task 8: Rename Logging and Undo

**Files:**
- Create: `src/offline_npu_renamer/core/logging.py`
- Test: `tests/test_logging.py`

- [ ] **Step 1: Write log tests**

Write `tests/test_logging.py`:

```python
from pathlib import Path

from offline_npu_renamer.core.logging import RenameRecord, append_record, read_records


def test_append_and_read_rename_records(tmp_path):
    log_path = tmp_path / "rename-log.jsonl"
    record = RenameRecord(
        timestamp="2026-05-30T10:00:00",
        original_path=str(tmp_path / "old.txt"),
        new_path=str(tmp_path / "2026-05-30_old.txt"),
        original_filename="old.txt",
        new_filename="2026-05-30_old.txt",
        file_type="document",
        date_source="content",
        analyzer_id="text-direct",
        confidence=0.75,
    )

    append_record(log_path, record)

    assert read_records(log_path) == [record]
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_logging.py -v`

Expected: FAIL because logging module does not exist.

- [ ] **Step 3: Implement JSON Lines logging**

Write `src/offline_npu_renamer/core/logging.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenameRecord:
    timestamp: str
    original_path: str
    new_path: str
    original_filename: str
    new_filename: str
    file_type: str
    date_source: str
    analyzer_id: str
    confidence: float


def append_record(log_path: Path, record: RenameRecord) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def read_records(log_path: Path) -> list[RenameRecord]:
    if not log_path.exists():
        return []
    records: list[RenameRecord] = []
    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(RenameRecord(**json.loads(line)))
    return records
```

- [ ] **Step 4: Verify logging tests pass**

Run: `pytest tests/test_logging.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/logging.py tests/test_logging.py
git commit -m "feat: write undoable rename logs"
```

## Task 9: Rename Apply and Undo

**Files:**
- Create: `src/offline_npu_renamer/core/renamer.py`
- Test: `tests/test_renamer.py`

- [ ] **Step 1: Write rename tests**

Write `tests/test_renamer.py`:

```python
from offline_npu_renamer.core.logging import read_records
from offline_npu_renamer.core.models import DateSource, FileKind, RenameSuggestion
from offline_npu_renamer.core.renamer import apply_renames, undo_latest


def test_apply_renames_and_undo_latest(tmp_path):
    source = tmp_path / "old.txt"
    source.write_text("hello", encoding="utf-8")
    target = tmp_path / "2026-05-30_old.txt"
    log_path = tmp_path / "rename-log.jsonl"
    suggestion = RenameSuggestion(
        source_path=source,
        target_path=target,
        file_kind=FileKind.DOCUMENT,
        date_source=DateSource.CONTENT,
        confidence=0.8,
        reason="test",
    )

    results = apply_renames([suggestion], log_path)

    assert results == [(source, target, "renamed")]
    assert not source.exists()
    assert target.exists()
    assert len(read_records(log_path)) == 1

    undo_results = undo_latest(log_path)

    assert undo_results == [(target, source, "undone")]
    assert source.exists()
    assert not target.exists()
```

- [ ] **Step 2: Run the failing tests**

Run: `pytest tests/test_renamer.py -v`

Expected: FAIL because renamer module does not exist.

- [ ] **Step 3: Implement apply and undo**

Write `src/offline_npu_renamer/core/renamer.py`:

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from offline_npu_renamer.core.logging import RenameRecord, append_record, read_records
from offline_npu_renamer.core.models import RenameSuggestion, SuggestionStatus


def apply_renames(
    suggestions: list[RenameSuggestion],
    log_path: Path,
) -> list[tuple[Path, Path, str]]:
    results: list[tuple[Path, Path, str]] = []
    for suggestion in suggestions:
        source = suggestion.source_path
        target = suggestion.target_path
        if suggestion.status is not SuggestionStatus.READY:
            results.append((source, target, "skipped-not-ready"))
            continue
        if not source.exists():
            results.append((source, target, "skipped-missing-source"))
            continue
        if target.exists() and target.resolve() != source.resolve():
            results.append((source, target, "skipped-existing-target"))
            continue
        source.rename(target)
        append_record(
            log_path,
            RenameRecord(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                original_path=str(source),
                new_path=str(target),
                original_filename=source.name,
                new_filename=target.name,
                file_type=suggestion.file_kind.value,
                date_source=suggestion.date_source.value,
                analyzer_id="local-analyzer",
                confidence=suggestion.confidence,
            ),
        )
        results.append((source, target, "renamed"))
    return results


def undo_latest(log_path: Path) -> list[tuple[Path, Path, str]]:
    records = read_records(log_path)
    results: list[tuple[Path, Path, str]] = []
    for record in reversed(records):
        current = Path(record.new_path)
        original = Path(record.original_path)
        if not current.exists():
            results.append((current, original, "skipped-missing-current"))
            continue
        if original.exists():
            results.append((current, original, "skipped-existing-original"))
            continue
        current.rename(original)
        results.append((current, original, "undone"))
    return results
```

- [ ] **Step 4: Verify rename tests pass**

Run: `pytest tests/test_renamer.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/offline_npu_renamer/core/renamer.py tests/test_renamer.py
git commit -m "feat: apply and undo rename operations"
```

## Task 10: Desktop UI

**Files:**
- Create: `src/offline_npu_renamer/app.py`
- Create: `src/offline_npu_renamer/ui/main_window.py`
- Test: `tests/test_app_import.py`

- [ ] **Step 1: Write import smoke test**

Write `tests/test_app_import.py`:

```python
def test_app_entrypoint_imports():
    from offline_npu_renamer.app import main

    assert callable(main)
```

- [ ] **Step 2: Run the failing test**

Run: `pytest tests/test_app_import.py -v`

Expected: FAIL because app module does not exist.

- [ ] **Step 3: Implement app entrypoint**

Write `src/offline_npu_renamer/app.py`:

```python
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from offline_npu_renamer.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1100, 700)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Implement main window**

Write `src/offline_npu_renamer/ui/main_window.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from offline_npu_renamer.core.analyzer import analyze_file
from offline_npu_renamer.core.model_assets import validate_model_assets
from offline_npu_renamer.core.models import RenameSuggestion, SuggestionStatus
from offline_npu_renamer.core.npu import detect_npu_status
from offline_npu_renamer.core.renamer import apply_renames, undo_latest
from offline_npu_renamer.core.scanner import scan_folder


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Offline NPU Renamer")
        self.selected_folder: Path | None = None
        self.suggestions: list[RenameSuggestion] = []
        self.model_status = validate_model_assets(Path("models") / "manifest.json")
        self.npu_status = detect_npu_status()

        self.status_label = QLabel(self._startup_message())
        self.folder_label = QLabel("No folder selected")
        self.choose_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan")
        self.apply_button = QPushButton("Apply Renames")
        self.undo_button = QPushButton("Undo Latest")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Include", "Original", "Suggested", "Type", "Date Source", "Confidence", "Reason"]
        )

        self.choose_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.scan)
        self.apply_button.clicked.connect(self.apply)
        self.undo_button.clicked.connect(self.undo)

        top = QHBoxLayout()
        top.addWidget(self.choose_button)
        top.addWidget(self.scan_button)
        top.addWidget(self.apply_button)
        top.addWidget(self.undo_button)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.folder_label)
        layout.addLayout(top)
        layout.addWidget(self.table)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder")
        if folder:
            self.selected_folder = Path(folder)
            self.folder_label.setText(str(self.selected_folder))

    def scan(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        if not self.model_status.available:
            QMessageBox.warning(self, "Models unavailable", self.model_status.message)
            return
        if not self.npu_status.available:
            QMessageBox.warning(self, "NPU unavailable", self.npu_status.message)
            return
        scanned = scan_folder(self.selected_folder)
        self.suggestions = [
            analyze_file(item.path, item.kind, self.npu_status, today=date.today())
            for item in scanned
        ]
        self.populate_table()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.suggestions))
        for row, suggestion in enumerate(self.suggestions):
            include = QTableWidgetItem("yes" if suggestion.status is SuggestionStatus.READY else "no")
            values = [
                include,
                QTableWidgetItem(suggestion.source_path.name),
                QTableWidgetItem(suggestion.target_path.name),
                QTableWidgetItem(suggestion.file_kind.value),
                QTableWidgetItem(suggestion.date_source.value),
                QTableWidgetItem(f"{suggestion.confidence:.2f}"),
                QTableWidgetItem(suggestion.reason),
            ]
            for column, item in enumerate(values):
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def apply(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        selected = [
            suggestion
            for row, suggestion in enumerate(self.suggestions)
            if self.table.item(row, 0) and self.table.item(row, 0).text().lower() == "yes"
        ]
        results = apply_renames(selected, self.selected_folder / "rename-log.jsonl")
        QMessageBox.information(self, "Rename complete", f"Processed {len(results)} file(s).")

    def undo(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        results = undo_latest(self.selected_folder / "rename-log.jsonl")
        QMessageBox.information(self, "Undo complete", f"Processed {len(results)} file(s).")

    def _startup_message(self) -> str:
        if not self.model_status.available:
            return self.model_status.message
        if not self.npu_status.available:
            return self.npu_status.message
        return f"{self.model_status.message} {self.npu_status.message}"
```

- [ ] **Step 5: Verify app import test passes**

Run: `pytest tests/test_app_import.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/offline_npu_renamer/app.py src/offline_npu_renamer/ui/main_window.py tests/test_app_import.py
git commit -m "feat: add desktop rename preview UI"
```

## Task 11: Bundled Model Manifest, Assets, and Final Verification

**Files:**
- Create: `models/manifest.json`
- Add: `models/document-title-v1.onnx`
- Add: `models/image-title-v1.onnx`
- Modify: `README.md`

- [ ] **Step 1: Add bundled model manifest**

Write `models/manifest.json` after the actual model files are selected and placed in `models/`. The `sha256` values must be the real SHA-256 values computed from the bundled files:

```json
{
  "version": 1,
  "models": [
    {
      "id": "document-title-v1",
      "path": "document-title-v1.onnx",
      "task": "document-title",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "required_provider": "QNNExecutionProvider"
    },
    {
      "id": "image-title-v1",
      "path": "image-title-v1.onnx",
      "task": "image-title",
      "sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
      "required_provider": "QNNExecutionProvider"
    }
  ]
}
```

- [ ] **Step 2: Add bundled model files**

Place the selected offline ONNX model files at:

```text
models/document-title-v1.onnx
models/image-title-v1.onnx
```

If the files are larger than normal Git hosting limits, track them with Git LFS before committing:

```powershell
git lfs install
git lfs track "*.onnx"
git add .gitattributes models/document-title-v1.onnx models/image-title-v1.onnx
```

Compute hashes and update `models/manifest.json`:

```powershell
Get-FileHash models/document-title-v1.onnx -Algorithm SHA256
Get-FileHash models/image-title-v1.onnx -Algorithm SHA256
```

Expected: the manifest contains the exact SHA-256 value for each bundled model, replacing the illustrative hash strings from the manifest skeleton.

- [ ] **Step 3: Expand README model note**

Append to `README.md`:

```markdown

## Bundled offline models

The first version includes ONNX model files in `models/`. The app validates `models/manifest.json`, checks that every bundled model exists, and verifies each SHA-256 hash before analysis starts.

The app must not download models at runtime. If a bundled model is missing, corrupted, or incompatible with the selected NPU provider, analysis is disabled.

## NPU policy

The app checks ONNX Runtime execution providers at startup. Supported NPU-backed providers are listed in `src/offline_npu_renamer/core/npu.py`.

If only CPU or GPU providers are available, analysis is disabled. File enumeration and parsing still use normal CPU work because Windows cannot perform filesystem and decoding operations entirely on the NPU.
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`

Expected: all tests PASS.

- [ ] **Step 5: Run the app smoke check**

Run: `python -m offline_npu_renamer.app`

Expected: app window opens. If no supported NPU provider exists or bundled model validation fails, the top status label explains that analysis is disabled.

- [ ] **Step 6: Commit**

```powershell
git add models/manifest.json models/document-title-v1.onnx models/image-title-v1.onnx README.md
git commit -m "feat: bundle offline ONNX models"
```

## Self-Review

- Spec coverage: The plan covers folder selection, non-recursive scan, document and image support, bundled model validation, NPU gating, preview, dated filename generation, collision suffixes, apply rename, JSON Lines log, undo, and offline model packaging.
- First-version model requirement: Document and image model files are bundled with the app distribution and verified from `models/manifest.json`. The NPU gate remains strict, so the app does not perform AI inference on CPU or GPU.
- Red-flag scan: The plan has been checked for unresolved design contradictions.
- Type consistency: Shared dataclasses from `core.models` are used consistently by scanner, analyzer, renamer, and UI tasks.
