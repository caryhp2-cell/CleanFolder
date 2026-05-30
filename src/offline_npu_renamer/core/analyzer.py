from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from offline_npu_renamer.core.extractors import extract_document_content, extract_image_content
from offline_npu_renamer.core.filenames import build_target_path, choose_date, find_content_dates
from offline_npu_renamer.core.models import (
    DateSource,
    FileKind,
    ModelAssetStatus,
    NpuStatus,
    RenameSuggestion,
    SuggestionStatus,
)


def analyze_file(
    path: Path,
    file_kind: FileKind,
    npu_status: NpuStatus,
    model_status: ModelAssetStatus,
    today: date | None = None,
) -> RenameSuggestion:
    if not model_status.available:
        return _blocked(path, file_kind, model_status.message)
    if not npu_status.available:
        return _blocked(path, file_kind, npu_status.message)

    current_date = today or date.today()
    try:
        content = (
            extract_document_content(path)
            if file_kind is FileKind.DOCUMENT
            else extract_image_content(path)
        )
    except Exception as error:
        return RenameSuggestion(
            source_path=path,
            target_path=path,
            file_kind=file_kind,
            date_source=DateSource.CURRENT_DATE,
            confidence=0.0,
            reason=f"Analyzer failed: {error}",
            status=SuggestionStatus.ERROR,
        )

    title = _best_title_candidate(content.text, path.stem)
    modified_date = datetime.fromtimestamp(path.stat().st_mtime).date()
    chosen_date = choose_date(
        content_dates=find_content_dates(content.text),
        metadata_date=content.metadata_date,
        modified_date=modified_date,
        today=current_date,
    )
    target = build_target_path(path, chosen_date.value, title)
    confidence = 0.82 if chosen_date.source is DateSource.CONTENT else 0.62
    return RenameSuggestion(
        source_path=path,
        target_path=target,
        file_kind=file_kind,
        date_source=chosen_date.source,
        confidence=confidence,
        reason=f"{content.analyzer_id} produced a local offline suggestion.",
        status=SuggestionStatus.READY,
    )


def _blocked(path: Path, file_kind: FileKind, reason: str) -> RenameSuggestion:
    return RenameSuggestion(
        source_path=path,
        target_path=path,
        file_kind=file_kind,
        date_source=DateSource.CURRENT_DATE,
        confidence=0.0,
        reason=reason,
        status=SuggestionStatus.ERROR,
    )


def _best_title_candidate(text: str, fallback: str) -> str:
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("#").strip()
        if 4 <= len(line) <= 120:
            candidates.append(line)
    if candidates:
        return candidates[0]
    compact = " ".join(text.split())
    if compact:
        return compact[:80]
    return fallback
