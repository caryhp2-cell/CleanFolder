# Article LLM Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace rule-based Article Analysis with a local Phi-3.5 Mini ONNX DirectML analyzer.

**Architecture:** Keep the UI thin. Move LLM generation and JSON validation into focused core modules. Load ONNX Runtime GenAI lazily so normal imports and tests stay fast.

**Tech Stack:** Python 3.11, pytest, PySide6, ONNX Runtime GenAI, Hugging Face Hub, DirectML.

---

## File Structure

- `src/offline_npu_renamer/core/article_analysis.py`: validates article text, calls an injected or default generator, returns `ArticleAnalysisResult`.
- `src/offline_npu_renamer/core/article_llm.py`: lazy Phi ONNX Runtime GenAI wrapper and prompt formatting.
- `src/offline_npu_renamer/core/model_assets.py`: supports directory-based model assets with per-file hashes.
- `src/offline_npu_renamer/ui/main_window.py`: removes the NPU gate from Article Analysis and displays LLM route errors.
- `scripts/fetch_models.py`: can fetch the Phi DirectML INT4 asset directory and write required file hashes.
- `tests/test_article_analysis.py`: fake-generator behavior tests.
- `tests/test_model_assets.py`: directory manifest validation tests.
- `tests/test_app_import.py`: verifies app import does not import the heavy LLM runtime.
- `README.md`: documents Article Analysis DirectML GPU route.

## Task 1: Article Analysis Contract

**Files:**
- Modify: `tests/test_article_analysis.py`
- Modify: `src/offline_npu_renamer/core/article_analysis.py`

- [ ] **Step 1: Write failing tests**

Replace article tests with fake-generator tests for valid JSON, invalid JSON, hallucinated key sentences, empty input, and generator failure.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_article_analysis.py -v`

Expected: FAIL because `generator` injection and LLM validation are not implemented.

- [ ] **Step 3: Implement minimal analyzer**

Implement `analyze_article_text(text, generator=None)` so it strips text, calls a generator, parses JSON, validates fields, checks key sentence matches, and returns `ERROR` without extractive fallback when anything fails.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_article_analysis.py -v`

Expected: PASS.

## Task 2: Directory Model Validation

**Files:**
- Modify: `tests/test_model_assets.py`
- Modify: `src/offline_npu_renamer/core/model_assets.py`

- [ ] **Step 1: Write failing test**

Add a manifest test where a model points to a directory and lists `required_files` with per-file SHA-256 hashes.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_model_assets.py -v`

Expected: FAIL because `required_files` is not supported.

- [ ] **Step 3: Implement directory support**

Extend `ModelSpec` with `source_repo`, `source_subdir`, and `required_files`. Validate single-file models with `sha256` as before and directory models with the required file list.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_model_assets.py -v`

Expected: PASS.

## Task 3: Lazy Phi Runtime

**Files:**
- Create: `src/offline_npu_renamer/core/article_llm.py`
- Modify: `tests/test_app_import.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing lazy-import test**

Assert importing `offline_npu_renamer.app` does not load `onnxruntime_genai` into `sys.modules`.

- [ ] **Step 2: Verify red or guard**

Run: `pytest tests/test_app_import.py -v`

Expected: PASS if the current app already avoids importing GenAI, then use it as a regression guard.

- [ ] **Step 3: Implement runtime wrapper**

Create `PhiArticleGenerator` that imports `onnxruntime_genai` inside `generate()`, formats a JSON-only prompt, verifies `DmlExecutionProvider` through `onnxruntime.get_available_providers()`, and returns generated text.

- [ ] **Step 4: Verify focused tests**

Run: `pytest tests/test_app_import.py tests/test_article_analysis.py -v`

Expected: PASS.

## Task 4: UI Wiring

**Files:**
- Modify: `src/offline_npu_renamer/ui/main_window.py`

- [ ] **Step 1: Update Article Analysis path**

Remove model/NPU gate checks from `analyze_article`. Extract text, call `analyze_article_text(content.text)`, and display any `ERROR` reason.

- [ ] **Step 2: Verify import smoke**

Run: `pytest tests/test_app_import.py -v`

Expected: PASS.

## Task 5: Fetch Script and Docs

**Files:**
- Modify: `scripts/fetch_models.py`
- Modify: `README.md`

- [ ] **Step 1: Extend fetch script**

Add Phi file constants for `gpu/gpu-int4-awq-block-128` and write `required_files` hash entries to `models/manifest.json`.

- [ ] **Step 2: Update README**

Document that Article Analysis uses the Phi DirectML GPU route, requires local model assets, and does not silently fall back to another analyzer.

- [ ] **Step 3: Final verification**

Run: `pytest -v`

Expected: PASS. The optional real model check remains manual through `RUN_REAL_ARTICLE_LLM=1`.

## Self-Review

- Spec coverage: DirectML-only Article Analysis, no extractive fallback, fake-generator tests, directory assets, lazy runtime, UI errors, and README updates are covered.
- Placeholder scan: no open placeholders remain in this plan.
- Type consistency: `ArticleAnalysisResult`, `ModelAssetStatus`, `SuggestionStatus`, and generator injection are reused from existing core models.
