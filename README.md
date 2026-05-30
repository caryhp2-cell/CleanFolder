# Offline NPU Renamer

Windows desktop app for offline, content-based file rename suggestions.

The first version supports documents and images. AI analysis is gated by bundled model validation and NPU availability. If bundled model files are missing, hashes do not match, or no supported NPU-backed ONNX Runtime provider is available, the app disables analysis instead of falling back to CPU or GPU inference.

## Selected bundled model route

- Documents: `Xenova/paraphrase-multilingual-MiniLM-L12-v2` ONNX, used as the bundled multilingual text understanding model.
- Images: `SWHL/RapidOCR` PP-OCRv4 ONNX models, used as the bundled OCR route for image text extraction.

The app validates `models/manifest.json`, checks that every bundled model exists, verifies each SHA-256 hash, and attempts to create ONNX Runtime sessions with the selected NPU execution provider.

## NPU policy

The app does not silently use CPU or GPU for AI inference. On this Intel Core Ultra 5 225H machine, the supported route is:

- `onnxruntime-openvino==1.24.1`
- `openvino==2025.4.1`
- `OpenVINOExecutionProvider` configured with `device_type=NPU`

File enumeration, parsing, image decoding, filename cleanup, and log writes still use normal CPU work because those are not NPU inference tasks.

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

That script downloads the selected models once, writes `models/manifest.json`, and records SHA-256 hashes. The installed app can then run offline.
