from offline_npu_renamer.core.extractors import extract_document_content


def test_pdf_without_embedded_text_falls_back_to_page_images(monkeypatch, tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.4 fake")

    class FakePage:
        def extract_text(self):
            return ""

    class FakeReader:
        metadata = None
        pages = [FakePage(), FakePage()]

    monkeypatch.setattr(
        "offline_npu_renamer.core.extractors.PdfReader",
        lambda _: FakeReader(),
    )
    monkeypatch.setattr(
        "offline_npu_renamer.core.extractors.extract_pdf_image_text",
        lambda _: "OCR text from scanned PDF",
    )

    content = extract_document_content(path)

    assert content.text == "OCR text from scanned PDF"
    assert content.analyzer_id == "pdf-image-ocr"
