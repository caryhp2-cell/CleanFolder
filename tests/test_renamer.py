from offline_npu_renamer.core.models import DateSource, FileKind, RenameSuggestion
from offline_npu_renamer.core.rename_log import read_records
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
