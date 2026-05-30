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
    cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", cleaned)
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
