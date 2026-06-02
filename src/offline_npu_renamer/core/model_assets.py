from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import onnxruntime as ort

from offline_npu_renamer.core.models import ModelAssetStatus, NpuStatus


@dataclass(frozen=True)
class ModelFileSpec:
    path: Path
    sha256: str


@dataclass(frozen=True)
class ModelSpec:
    id: str
    path: Path
    task: str
    sha256: str | None
    required_provider: str
    required_files: tuple[ModelFileSpec, ...] = ()


_DLL_DIRECTORY_HANDLES: list[object] = []


def default_models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "models"


def load_manifest(manifest_path: Path | None = None) -> list[ModelSpec]:
    path = manifest_path or default_models_dir() / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    specs: list[ModelSpec] = []
    for item in manifest.get("models", []):
        model_path = (root / str(item["path"])).resolve()
        specs.append(
            ModelSpec(
                id=str(item["id"]),
                path=model_path,
                task=str(item["task"]),
                sha256=str(item["sha256"]).lower() if "sha256" in item else None,
                required_provider=str(item["required_provider"]),
                required_files=tuple(
                    ModelFileSpec(
                        path=(model_path / str(file_item["path"])).resolve(),
                        sha256=str(file_item["sha256"]).lower(),
                    )
                    for file_item in item.get("required_files", [])
                ),
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
        if spec.required_files:
            if not spec.path.exists() or not spec.path.is_dir():
                return ModelAssetStatus(False, f"Missing bundled model directory: {spec.id}", tuple(seen))
            for file_spec in spec.required_files:
                if not file_spec.path.exists():
                    return ModelAssetStatus(False, f"Missing bundled model file: {spec.id}", tuple(seen))
                actual_hash = sha256_file(file_spec.path)
                if actual_hash != file_spec.sha256:
                    return ModelAssetStatus(False, f"Bundled model hash mismatch for {spec.id}", tuple(seen))
        else:
            if spec.sha256 is None:
                return ModelAssetStatus(False, f"Bundled model manifest missing hash for {spec.id}", tuple(seen))
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

    if npu_status.provider == "OpenVINOExecutionProvider":
        add_openvino_dll_directory()

    provider_options: list[dict[str, Any]] | None = (
        list(npu_status.provider_options) if npu_status.provider_options else None
    )
    for spec in load_manifest(manifest_path or default_models_dir() / "manifest.json"):
        if spec.required_files:
            continue
        try:
            session = ort.InferenceSession(
                str(spec.path),
                providers=[npu_status.provider],
                provider_options=provider_options,
            )
            if session.get_providers()[0] != npu_status.provider:
                return ModelAssetStatus(
                    False,
                    f"Bundled model did not bind to {npu_status.provider}: {spec.id}",
                    asset_status.model_ids,
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


def add_openvino_dll_directory() -> None:
    try:
        import openvino
    except ImportError:
        return

    libs_dir = Path(openvino.__file__).resolve().parent / "libs"
    if not libs_dir.exists():
        return
    os.environ["PATH"] = f"{libs_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    if hasattr(os, "add_dll_directory"):
        handle = os.add_dll_directory(str(libs_dir))
        _DLL_DIRECTORY_HANDLES.append(handle)
