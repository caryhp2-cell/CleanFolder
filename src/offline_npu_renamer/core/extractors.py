from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from docx import Document
from PIL import Image
from pypdf import PdfReader

from offline_npu_renamer.core.models import ExtractedContent

_OCR_ENGINE: Any | None = None


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
        if not text.strip():
            return ExtractedContent(
                text=extract_pdf_image_text(path),
                metadata_date=metadata_date,
                analyzer_id="pdf-image-ocr",
            )
        return ExtractedContent(text=text, metadata_date=metadata_date, analyzer_id="pdf-text+minilm")
    if suffix == ".docx":
        document = Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return ExtractedContent(text=text, metadata_date=None, analyzer_id="docx-text+minilm")
    raise ValueError(f"Unsupported document type: {path.suffix}")


def extract_image_content(path: Path) -> ExtractedContent:
    text = extract_image_text(path)
    if not text:
        with Image.open(path) as image:
            width, height = image.size
        text = f"{path.stem.replace('_', ' ')} image {width}x{height}"
    return ExtractedContent(text=text, metadata_date=None, analyzer_id="ppocrv4-onnx")


def extract_pdf_image_text(path: Path, max_pages: int = 5) -> str:
    import fitz

    extracted: list[str] = []
    with TemporaryDirectory() as temp_dir:
        document = fitz.open(path)
        for page_index in range(min(max_pages, document.page_count)):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = Path(temp_dir) / f"page-{page_index + 1}.png"
            pixmap.save(str(image_path))
            extracted.append(extract_image_text(image_path))
    return "\n".join(part for part in extracted if part.strip())


def extract_image_text(path: Path) -> str:
    engine = _get_ocr_engine()
    result = engine(str(path), use_cls=False)
    texts = getattr(result, "txts", None) or ()
    return "\n".join(str(text) for text in texts if str(text).strip())


def _get_ocr_engine() -> Any:
    global _OCR_ENGINE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE

    from rapidocr import RapidOCR
    from rapidocr.inference_engine.onnxruntime.provider_config import ProviderConfig

    from offline_npu_renamer.core.model_assets import add_openvino_dll_directory, default_models_dir

    add_openvino_dll_directory()

    def openvino_provider_list(self: Any) -> list[tuple[str, dict[str, str]]]:
        return [("OpenVINOExecutionProvider", {"device_type": "NPU"}), ("CPUExecutionProvider", {})]

    def verify_openvino_first(self: Any, session_providers: list[str]) -> None:
        if not session_providers or session_providers[0] != "OpenVINOExecutionProvider":
            raise RuntimeError(f"OCR model did not bind to OpenVINOExecutionProvider: {session_providers}")

    ProviderConfig.get_ep_list = openvino_provider_list  # type: ignore[method-assign]
    ProviderConfig.verify_providers = verify_openvino_first  # type: ignore[method-assign]

    models_dir = default_models_dir()
    _OCR_ENGINE = RapidOCR(
        params={
            "Global.use_cls": False,
            "Global.log_level": "warning",
            "Det.model_path": str(models_dir / "image-ocr-det-v1.onnx"),
            "Cls.model_path": str(models_dir / "image-ocr-cls-v1.onnx"),
            "Rec.model_path": str(models_dir / "image-ocr-rec-v1.onnx"),
        }
    )
    return _OCR_ENGINE


def _normalize_pdf_date(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return None
