# Offline NPU File Renamer Design

## Goal

Build a Windows desktop app that renames files based on their content. The app runs offline, lets the user choose a folder, analyzes supported files, proposes new names with a date prefix, and only renames files after user confirmation.

The first version supports documents and images. The architecture should allow audio and video analyzers to be added later.

## Core User Flow

1. User opens the app.
2. User selects a folder.
3. App validates that bundled offline model files are present and match the expected hashes.
4. App detects whether an NPU-backed inference provider is available.
5. If bundled models or NPU inference are unavailable, the app stops analysis and explains why.
6. If bundled models and NPU inference are available, the app scans supported files in the selected folder.
7. App analyzes file content and generates rename suggestions.
8. App shows a preview table with the original name, suggested name, date source, confidence, and reason.
9. User confirms the selected rename operations.
10. App renames files and writes an undoable log.

## First-Version Scope

Supported document types:

- `.txt`
- `.md`
- `.pdf`
- `.docx`

Supported image types:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.tiff`

Out of scope for the first version:

- Audio and video content analysis.
- Cloud model calls or online API usage.
- Fully automatic renaming without preview.
- Recursive rename by default. Recursive scanning can be added as an explicit option later.
- Runtime model downloads. First-version model files must be bundled with the app or installer.

## Recommended Technology

Use a Python Windows desktop app for the first version.

Suggested stack:

- UI: PySide6 or CustomTkinter.
- Local inference: ONNX Runtime.
- Model format: bundled ONNX models with a checked-in manifest and packaged binary assets.
- Document extraction: local parsers for text, Markdown, PDF, and DOCX.
- Document AI: bundled local model for title/summary generation from extracted text.
- Image AI: bundled local OCR or vision model for image-derived rename suggestions.
- Storage: local JSON Lines rename log.

Python keeps the first version fast to build while still allowing Windows-specific NPU provider checks through ONNX Runtime.

## NPU Policy

The app should prioritize NPU and must not silently fall back to CPU or GPU for AI inference.

Startup behavior:

1. Load the bundled model manifest.
2. Verify required model files exist inside the app package or installed model directory.
3. Verify each model file hash matches the manifest.
4. Inspect ONNX Runtime available execution providers.
5. Determine whether a supported NPU-backed provider is available for the current machine.
6. Verify required models can be loaded with the selected NPU-backed provider.
7. If a bundled model is missing, hash verification fails, or no NPU-backed provider is available, disable content analysis and show a clear message.
8. Do not run AI inference on CPU or GPU unless a later explicit setting is added.

Important limitation:

Some non-AI work will still use small amounts of CPU. This includes file enumeration, file reading, PDF parsing, image decoding, filename cleanup, and writing logs. The strict NPU requirement applies to AI inference.

## Bundled Offline Models

The first version must include offline model assets as part of the app distribution. The app must not require the user to download a model after installation.

The installed app should include:

- `models/manifest.json`
- A document title or summarization ONNX model.
- An image OCR or image understanding ONNX model.
- SHA-256 hashes for every model file.
- Required provider metadata for each model.

If bundled model validation fails, the app must not analyze or rename files. It should display which model is missing, corrupted, or incompatible with the selected NPU provider.

## Rename Format

Suggested filenames use this format:

```text
YYYY-MM-DD_<content-title-or-summary>.<extension>
```

Examples:

```text
2026-05-30_invoice_acme_may_payment.pdf
2026-05-30_meeting_notes_product_review.docx
2026-05-30_whiteboard_architecture_sketch.png
```

Date source priority:

1. Date detected in file content.
2. File metadata date.
3. File modified date.
4. Current local date as the final fallback.

The preview must show which date source was used.

Filename cleanup rules:

- Lowercase generated title text.
- Replace spaces with underscores.
- Remove Windows-invalid filename characters.
- Collapse repeated separators.
- Limit the generated title length.
- Preserve the original extension.
- Avoid collisions by appending `-2`, `-3`, and so on.

## Analysis Pipeline

Each file is processed through a common analyzer interface:

1. Detect file type.
2. Extract content or visual text.
3. Run bundled local NPU-backed inference for semantic understanding.
4. Generate a short filename title.
5. Detect or choose the best date.
6. Return a rename suggestion with confidence and reason.

Document analyzer:

- Text and Markdown: read text directly.
- PDF: extract text locally; use the bundled image model for image-only pages when pages are rendered as images.
- DOCX: extract paragraph text locally.
- Use the bundled document model to produce the title/summary used in the filename.

Image analyzer:

- Load image locally.
- Use the bundled local OCR or vision model.
- Generate a title from detected text or visual content.

## Preview UI

The preview table should include:

- Include checkbox.
- Original filename.
- Suggested filename.
- File type.
- Date source.
- Confidence score.
- Short reason.
- Status or warning.

The user can deselect files before applying rename operations.

## Rename Safety

The app must not rename files immediately after scanning.

Before rename:

- Validate every target filename.
- Detect collisions.
- Ensure target paths stay inside the selected folder.
- Show warnings for low-confidence suggestions.

During rename:

- Rename selected files only.
- Skip files that changed or disappeared after preview.
- Preserve extensions.
- Record every successful rename in the log.

## Undo Log

Write rename records to a local JSON Lines file, such as:

```text
rename-log.jsonl
```

Each record should include:

- Timestamp.
- Original path.
- New path.
- Original filename.
- New filename.
- File type.
- Date source.
- Model or analyzer identifier.
- Confidence.

Undo reads the latest applicable records and renames files back to their original paths when possible.

## Error Handling

The app should show clear messages for:

- No NPU-backed inference provider found.
- Bundled model file missing.
- Bundled model hash mismatch.
- Bundled model cannot load on the selected NPU provider.
- Folder cannot be read.
- Unsupported file type.
- File locked by another app.
- Target filename already exists.
- Analyzer failed.
- Rename failed.

Failures for one file should not stop preview generation for other files.

## Testing Plan

Unit tests:

- Filename cleanup.
- Date source priority.
- Collision handling.
- Supported file filtering.
- Rename log serialization.

Integration tests:

- Scan a temporary folder with sample documents and images.
- Generate preview suggestions without renaming.
- Apply selected renames.
- Undo applied renames.

Manual verification:

- Start app with NPU unavailable and confirm analysis is disabled.
- Start app with a missing bundled model and confirm analysis is disabled.
- Start app with a hash-mismatched bundled model and confirm analysis is disabled.
- Start app with NPU available and confirm inference uses the NPU provider.
- Verify the app works without network access.

## Future Extensions

- Recursive folder scanning.
- Audio transcript-based rename.
- Video frame and transcript analysis.
- User-editable filename templates.
- Per-folder rename profiles.
- Explicit advanced setting for CPU/GPU fallback, disabled by default.
