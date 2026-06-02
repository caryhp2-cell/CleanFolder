# Offline NPU Renamer

Windows desktop app for offline, content-based file rename suggestions.

The first version supports documents and images. Rename analysis is gated by bundled model validation and NPU availability. If bundled rename/OCR model files are missing, hashes do not match, or no supported NPU-backed ONNX Runtime provider is available, the app disables rename analysis instead of falling back to CPU or GPU inference.

## Features

- Rename: choose a folder, preview content-based dated filenames, apply selected renames, and undo from `rename-log.jsonl`.
- Article Analysis: choose a `.txt`, `.md`, `.pdf`, or `.docx` file and generate a local Phi-3.5 Mini ONNX summary with key sentences and a suggested title.

## Selected bundled model route

- Documents: `Xenova/paraphrase-multilingual-MiniLM-L12-v2` ONNX, used as the bundled multilingual text understanding model.
- Images: `SWHL/RapidOCR` PP-OCRv4 ONNX models, used as the bundled OCR route for image text extraction.
- Article Analysis: `microsoft/Phi-3.5-mini-instruct-onnx` GPU INT4 ONNX assets, used through ONNX Runtime GenAI and DirectML.

The app validates `models/manifest.json`, checks that every bundled model exists, verifies each SHA-256 hash, and attempts to create ONNX Runtime sessions with the selected NPU execution provider for rename/OCR models.

## NPU policy

The app does not silently use CPU or GPU for AI inference. On this Intel Core Ultra 5 225H machine, the supported route is:

- `onnxruntime-openvino==1.24.1`
- `openvino==2025.4.1`
- `OpenVINOExecutionProvider` configured with `device_type=NPU`

File enumeration, parsing, image decoding, filename cleanup, and log writes still use normal CPU work because those are not NPU inference tasks.

## Article Analysis GPU policy

Article Analysis uses the bundled Phi-3.5 Mini ONNX DirectML route instead of the rename/OCR NPU gate.

- Runtime package: `onnxruntime-genai-directml`
- Provider: `DmlExecutionProvider`
- Model assets: `models/phi-3.5-mini-instruct-onnx/gpu/gpu-int4-awq-block-128/`

The app does not silently fall back to the old extractive analyzer. If DirectML is unavailable, the Phi model files are missing, generation fails, or the model output cannot be validated as JSON, Article Analysis shows an error.

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

That script downloads the selected models once, writes `models/manifest.json`, and records SHA-256 hashes. The Phi Article Analysis model includes a large `model.onnx.data` file, so the first download can take a while. The installed app can then run offline.
