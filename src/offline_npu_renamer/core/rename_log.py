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
