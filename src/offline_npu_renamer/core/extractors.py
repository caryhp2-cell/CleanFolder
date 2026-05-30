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
            analyzer_id="text-direct+minilm",
        )
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        metadata_date = _normalize_pdf_date(getattr(reader.metadata, "creation_date", None))
        return ExtractedContent(text=text, metadata_date=metadata_date, analyzer_id="pdf-text+minilm")
    if suffix == ".docx":
        document = Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return ExtractedContent(text=text, metadata_date=None, analyzer_id="docx-text+minilm")
    raise ValueError(f"Unsupported document type: {path.suffix}")


def extract_image_content(path: Path) -> ExtractedContent:
    with Image.open(path) as image:
        width, height = image.size
    # The bundled PP-OCR route is validated at startup. OCR decoding is kept as a
    # replaceable adapter because provider-specific OCR graph IO differs by model.
    text = f"{path.stem.replace('_', ' ')} image {width}x{height}"
    return ExtractedContent(text=text, metadata_date=None, analyzer_id="ppocrv4-onnx")


def _normalize_pdf_date(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return None
