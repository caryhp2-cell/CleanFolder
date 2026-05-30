from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import onnxruntime as ort

from offline_npu_renamer.core.models import ModelAssetStatus, NpuStatus


@dataclass(frozen=True)
class ModelSpec:
    id: str
    path: Path
    task: str
    sha256: str
    required_provider: str


def default_models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "models"


def load_manifest(manifest_path: Path | None = None) -> list[ModelSpec]:
    path = manifest_path or default_models_dir() / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    specs: list[ModelSpec] = []
    for item in manifest.get("models", []):
        specs.append(
            ModelSpec(
                id=str(item["id"]),
                path=(root / str(item["path"])).resolve(),
                task=str(item["task"]),
                sha256=str(item["sha256"]).lower(),
                required_provider=str(item["required_provider"]),
            )
        )
    return specs


def validate_model_assets(manifest_path: Path | None = None) -> ModelAssetStatus:
    path = manifest_path or default_models_dir() / "manifest.json"
    if not path.exists():
        return ModelAssetStatus(False, f"Missing bundled model manifest: {path}", ())

    try:
        specs = load_manifest(path)
    except (KeyError, json.JSONDecodeError) as error:
        return ModelAssetStatus(False, f"Invalid bundled model manifest: {error}", ())

    if not specs:
        return ModelAssetStatus(False, "Bundled model manifest contains no models.", ())

    seen: list[str] = []
    for spec in specs:
        seen.append(spec.id)
        if not spec.path.exists():
            return ModelAssetStatus(False, f"Missing bundled model: {spec.id}", tuple(seen))
        actual_hash = sha256_file(spec.path)
        if actual_hash != spec.sha256:
            return ModelAssetStatus(False, f"Bundled model hash mismatch for {spec.id}", tuple(seen))

    return ModelAssetStatus(True, "Bundled offline models validated.", tuple(seen))


def validate_model_sessions(npu_status: NpuStatus, manifest_path: Path | None = None) -> ModelAssetStatus:
    asset_status = validate_model_assets(manifest_path)
    if not asset_status.available:
        return asset_status
    if not npu_status.available or npu_status.provider is None:
        return ModelAssetStatus(False, npu_status.message, asset_status.model_ids)

    provider_options: list[dict[str, Any]] | None = (
        list(npu_status.provider_options) if npu_status.provider_options else None
    )
    for spec in load_manifest(manifest_path or default_models_dir() / "manifest.json"):
        try:
            ort.InferenceSession(
                str(spec.path),
                providers=[npu_status.provider],
                provider_options=provider_options,
            )
        except Exception as error:
            return ModelAssetStatus(
                False,
                f"Bundled model cannot load on {npu_status.provider}: {spec.id}: {error}",
                asset_status.model_ids,
            )
    return ModelAssetStatus(True, "Bundled models load on selected NPU provider.", asset_status.model_ids)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
