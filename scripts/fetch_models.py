from __future__ import annotations

import json
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download

from offline_npu_renamer.core.model_assets import sha256_file

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"

MODEL_FILES = [
    {
        "repo_id": "Xenova/paraphrase-multilingual-MiniLM-L12-v2",
        "filename": "onnx/model_int8.onnx",
        "target": "document-title-v1.onnx",
        "id": "document-title-v1",
        "task": "document-title",
    },
    {
        "repo_id": "SWHL/RapidOCR",
        "filename": "PP-OCRv4/ch_PP-OCRv4_det_infer.onnx",
        "target": "image-ocr-det-v1.onnx",
        "id": "image-ocr-det-v1",
        "task": "image-ocr-detection",
    },
    {
        "repo_id": "SWHL/RapidOCR",
        "filename": "PP-OCRv1/ch_ppocr_mobile_v2.0_cls_infer.onnx",
        "target": "image-ocr-cls-v1.onnx",
        "id": "image-ocr-cls-v1",
        "task": "image-ocr-classification",
    },
    {
        "repo_id": "SWHL/RapidOCR",
        "filename": "PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx",
        "target": "image-ocr-rec-v1.onnx",
        "id": "image-ocr-rec-v1",
        "task": "image-ocr-recognition",
    },
]


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    manifest_models = []
    for item in MODEL_FILES:
        downloaded = Path(
            hf_hub_download(
                repo_id=item["repo_id"],
                filename=item["filename"],
            )
        )
        target = MODELS / item["target"]
        shutil.copyfile(downloaded, target)
        manifest_models.append(
            {
                "id": item["id"],
                "path": item["target"],
                "task": item["task"],
                "sha256": sha256_file(target),
                "required_provider": "OpenVINOExecutionProvider",
                "source_repo": item["repo_id"],
                "source_file": item["filename"],
            }
        )

    manifest = {
        "version": 1,
        "models": manifest_models,
        "npu_policy": {
            "no_cpu_or_gpu_ai_fallback": True,
            "preferred_providers": [
                "QNNExecutionProvider",
                "OpenVINOExecutionProvider",
                "VitisAIExecutionProvider",
            ],
        },
    }
    (MODELS / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {(MODELS / 'manifest.json')}")


if __name__ == "__main__":
    main()
