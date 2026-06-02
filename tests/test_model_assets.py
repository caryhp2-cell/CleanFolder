import hashlib
import json

from offline_npu_renamer.core.model_assets import validate_model_assets


def test_validate_model_assets_accepts_present_hashed_models(tmp_path):
    model_path = tmp_path / "document-title-v1.onnx"
    model_path.write_bytes(b"fake-onnx-bytes")
    digest = hashlib.sha256(b"fake-onnx-bytes").hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "document-title-v1",
                        "path": "document-title-v1.onnx",
                        "task": "document-title",
                        "sha256": digest,
                        "required_provider": "QNNExecutionProvider",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validate_model_assets(manifest_path)

    assert status.available is True
    assert status.message == "Bundled offline models validated."


def test_validate_model_assets_rejects_missing_model(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "image-title-v1",
                        "path": "image-title-v1.onnx",
                        "task": "image-title",
                        "sha256": "abc",
                        "required_provider": "QNNExecutionProvider",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validate_model_assets(manifest_path)

    assert status.available is False
    assert "Missing bundled model" in status.message


def test_validate_model_assets_accepts_directory_model_required_files(tmp_path):
    model_dir = tmp_path / "phi" / "gpu"
    model_dir.mkdir(parents=True)
    config = model_dir / "genai_config.json"
    onnx_model = model_dir / "model.onnx"
    config.write_bytes(b"fake-config")
    onnx_model.write_bytes(b"fake-model")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "article-llm-phi35-mini-directml-v1",
                        "path": "phi/gpu",
                        "task": "article-llm-analysis",
                        "required_provider": "DmlExecutionProvider",
                        "required_files": [
                            {
                                "path": "genai_config.json",
                                "sha256": hashlib.sha256(b"fake-config").hexdigest(),
                            },
                            {
                                "path": "model.onnx",
                                "sha256": hashlib.sha256(b"fake-model").hexdigest(),
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validate_model_assets(manifest_path)

    assert status.available is True
    assert status.model_ids == ("article-llm-phi35-mini-directml-v1",)
