from datetime import date

from offline_npu_renamer.core.analyzer import analyze_file
from offline_npu_renamer.core.models import DateSource, FileKind, ModelAssetStatus, NpuStatus


def test_analyze_file_requires_models(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Meeting Notes 2026-05-30", encoding="utf-8")

    suggestion = analyze_file(
        path=path,
        file_kind=FileKind.DOCUMENT,
        npu_status=NpuStatus(True, "QNNExecutionProvider", "ok", ("QNNExecutionProvider",)),
        model_status=ModelAssetStatus(False, "Missing bundled model", ()),
        today=date(2026, 5, 30),
    )

    assert suggestion.status.value == "error"
    assert suggestion.target_path == path
    assert "Missing bundled model" in suggestion.reason


def test_analyze_text_file_generates_content_date_name_when_gates_pass(tmp_path):
    path = tmp_path / "old.txt"
    path.write_text("Quarterly Planning 2026-05-30\nRoadmap review", encoding="utf-8")

    suggestion = analyze_file(
        path=path,
        file_kind=FileKind.DOCUMENT,
        npu_status=NpuStatus(True, "QNNExecutionProvider", "ok", ("QNNExecutionProvider",)),
        model_status=ModelAssetStatus(True, "models ok", ("document-title-v1",)),
        today=date(2026, 1, 1),
    )

    assert suggestion.status.value == "ready"
    assert suggestion.target_path.name == "2026-05-30_quarterly_planning_2026_05_30.txt"
    assert suggestion.date_source is DateSource.CONTENT
