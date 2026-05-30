from datetime import date

from offline_npu_renamer.core.filenames import build_target_path, clean_title, choose_date
from offline_npu_renamer.core.models import DateSource


def test_clean_title_removes_invalid_windows_characters():
    assert clean_title("Invoice: ACME / May*Payment?") == "invoice_acme_may_payment"


def test_clean_title_keeps_chinese_content():
    assert clean_title("會議記錄 產品 Review") == "會議記錄_產品_review"


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
