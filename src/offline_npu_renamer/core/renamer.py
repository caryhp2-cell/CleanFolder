from __future__ import annotations

from datetime import datetime
from pathlib import Path

from offline_npu_renamer.core.models import RenameSuggestion, SuggestionStatus
from offline_npu_renamer.core.rename_log import RenameRecord, append_record, read_records


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
        if source.resolve().parent != target.resolve().parent:
            results.append((source, target, "skipped-outside-folder"))
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
                analyzer_id="offline-npu-analyzer",
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
