from __future__ import annotations

import re
from pathlib import Path

from offline_npu_renamer.core.model_assets import default_models_dir, load_manifest

ARTICLE_LLM_TASK = "article-llm-analysis"
OPENVINO_GPU_DEVICE = "GPU"


class PhiArticleGenerator:
    def __init__(
        self,
        models_dir: Path | None = None,
        device: str = OPENVINO_GPU_DEVICE,
        max_article_chars: int = 12000,
        max_new_tokens: int = 260,
    ) -> None:
        self.models_dir = models_dir or default_models_dir()
        self.device = device
        self.max_article_chars = max_article_chars
        self.max_new_tokens = max_new_tokens
        self._pipeline: object | None = None

    def generate(self, text: str) -> str:
        pipeline = self._load_pipeline()
        prompt = _build_article_prompt(text[: self.max_article_chars])
        return str(
            pipeline.generate(
                prompt,
                max_new_tokens=self.max_new_tokens,
            )
        ).strip()

    def _load_pipeline(self) -> object:
        if self._pipeline is not None:
            return self._pipeline

        import openvino_genai as ov_genai

        model_dir = _article_model_dir(self.models_dir)
        self._pipeline = ov_genai.LLMPipeline(str(model_dir), self.device)
        return self._pipeline


def _article_model_dir(models_dir: Path) -> Path:
    manifest_path = models_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"Missing bundled model manifest: {manifest_path}")

    for spec in load_manifest(manifest_path):
        if spec.task == ARTICLE_LLM_TASK:
            if not spec.path.exists():
                raise RuntimeError(f"Missing Phi article model directory: {spec.path}")
            return spec.path
    raise RuntimeError("Phi article model is not listed in the bundled model manifest.")


def _build_article_prompt(article_text: str) -> str:
    source_sentences = _split_source_sentences(article_text)
    sentence_list = "\n".join(f"{index + 1}. {sentence}" for index, sentence in enumerate(source_sentences))
    return (
        "You are a strict JSON API. Return JSON only. Return exactly one valid JSON object. "
        "Stop immediately after the closing brace. Do not write Markdown. "
        "Do not write explanations outside JSON.\n\n"
        "The JSON object must have this exact shape:\n"
        '{"suggested_title":"...","summary":"...","key_sentences":["..."],"reason":"..."}'
        "\n\n"
        "Rules:\n"
        "- summary must be based only on the article\n"
        "- key_sentences must be copied exactly from the numbered source sentences below\n"
        "- no extra keys\n\n"
        "Numbered source sentences:\n"
        f"{sentence_list}\n\n"
        f"Article:\n{article_text}"
    )


def _split_source_sentences(article_text: str) -> list[str]:
    compact = " ".join(article_text.split())
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", compact) if part.strip()]
    return sentences or [compact]
