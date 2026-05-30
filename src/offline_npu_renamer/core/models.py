from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DateSource(str, Enum):
    CONTENT = "content"
    METADATA = "metadata"
    MODIFIED_TIME = "modified_time"
    CURRENT_DATE = "current_date"


class FileKind(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


class SuggestionStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NpuStatus:
    available: bool
    provider: str | None
    message: str
    available_providers: tuple[str, ...]
    provider_options: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class ModelAssetStatus:
    available: bool
    message: str
    model_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    metadata_date: str | None
    analyzer_id: str


@dataclass(frozen=True)
class RenameSuggestion:
    source_path: Path
    target_path: Path
    file_kind: FileKind
    date_source: DateSource
    confidence: float
    reason: str
    status: SuggestionStatus = SuggestionStatus.READY
