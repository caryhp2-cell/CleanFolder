# Offline NPU Renamer

Windows desktop app for offline, content-based file rename suggestions.

The first version supports documents and images. Rename analysis is gated by bundled model validation and NPU availability. If bundled rename/OCR model files are missing, hashes do not match, or no supported NPU-backed ONNX Runtime provider is available, the app disables rename analysis instead of falling back to CPU or GPU inference.

## Features

- Rename: choose a folder, preview content-based dated filenames, apply selected renames, and undo from `rename-log.jsonl`.
- Article Analysis: choose a `.txt`, `.md`, `.pdf`, or `.docx` file and generate a local Phi-3.5 Mini OpenVINO summary with key sentences and a suggested title.

## Selected bundled model route

- Documents: `Xenova/paraphrase-multilingual-MiniLM-L12-v2` ONNX, used as the bundled multilingual text understanding model.
- Images: `SWHL/RapidOCR` PP-OCRv4 ONNX models, used as the bundled OCR route for image text extraction.
- Article Analysis: `OpenVINO/Phi-3.5-mini-instruct-int4-ov` OpenVINO IR assets, used through OpenVINO GenAI on the integrated GPU.

The app validates `models/manifest.json`, checks that every bundled model exists, verifies each SHA-256 hash, and attempts to create ONNX Runtime sessions with the selected NPU execution provider for rename/OCR models.

## NPU policy

The app does not silently use CPU or GPU for AI inference. On this Intel Core Ultra 5 225H machine, the supported route is:

- `onnxruntime-openvino==1.24.1`
- `openvino==2025.4.1`
- `OpenVINOExecutionProvider` configured with `device_type=NPU`

File enumeration, parsing, image decoding, filename cleanup, and log writes still use normal CPU work because those are not NPU inference tasks.

## Article Analysis GPU policy

Article Analysis uses the bundled Phi-3.5 Mini OpenVINO INT4 GPU route instead of the rename/OCR NPU gate.

- Runtime package: `openvino-genai==2025.4.1.0`
- Provider: `GPU`
- Model assets: `models/openvino/Phi-3.5-mini-instruct-int4-ov/`

The app does not silently fall back to the old extractive analyzer. If the Phi model files are missing, generation fails, or the model output cannot be validated as JSON, Article Analysis shows an error.

ONNX Runtime GenAI with DirectML was tested for Phi-3.5 Mini, but the GPU asset failed initialization on this machine because DirectML graph capture could not support the model's control-flow nodes. OpenVINO GenAI with the OpenVINO INT4 model is the selected GPU route for this version.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
offline-npu-renamer
```

## Offline model files

The app expects bundled files in `models/` and never downloads models at runtime. During development, run:

```powershell
python scripts/fetch_models.py
```

That script downloads the selected models once, writes `models/manifest.json`, and records SHA-256 hashes. The Phi Article Analysis model includes a large `openvino_model.bin` file, so the first download can take a while. The installed app can then run offline.
