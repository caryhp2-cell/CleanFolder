from __future__ import annotations

import json
from pathlib import Path

from offline_npu_renamer.core.model_assets import default_models_dir, load_manifest

ARTICLE_LLM_TASK = "article-llm-analysis"
DIRECTML_PROVIDER = "DmlExecutionProvider"
GENAI_DIRECTML_PROVIDER = "dml"


class PhiArticleGenerator:
    def __init__(
        self,
        models_dir: Path | None = None,
        max_article_chars: int = 12000,
        max_new_tokens: int = 700,
    ) -> None:
        self.models_dir = models_dir or default_models_dir()
        self.max_article_chars = max_article_chars
        self.max_new_tokens = max_new_tokens
        self._model: object | None = None
        self._tokenizer: object | None = None

    def generate(self, text: str) -> str:
        self._ensure_directml_available()
        model, tokenizer, og = self._load_model()
        prompt = _build_article_prompt(text[: self.max_article_chars])
        input_message = [{"role": "user", "content": prompt}]
        input_prompt = tokenizer.apply_chat_template(
            json.dumps(input_message),
            add_generation_prompt=True,
        )
        input_tokens = tokenizer.encode(input_prompt)
        params = og.GeneratorParams(model)
        params.set_search_options(
            do_sample=False,
            max_length=len(input_tokens) + self.max_new_tokens,
            temperature=0.0,
        )
        generator = og.Generator(model, params)
        generator.append_tokens(input_tokens)
        stream = tokenizer.create_stream()
        output: list[str] = []
        while not generator.is_done():
            generator.generate_next_token()
            output.append(stream.decode(generator.get_next_tokens()[0]))
        return "".join(output).strip()

    def _load_model(self) -> tuple[object, object, object]:
        if self._model is not None and self._tokenizer is not None:
            import onnxruntime_genai as og

            return self._model, self._tokenizer, og

        import onnxruntime_genai as og

        model_dir = _article_model_dir(self.models_dir)
        config = og.Config(str(model_dir))
        config.clear_providers()
        config.append_provider(GENAI_DIRECTML_PROVIDER)
        self._model = og.Model(config)
        self._tokenizer = og.Tokenizer(self._model)
        return self._model, self._tokenizer, og

    def _ensure_directml_available(self) -> None:
        import onnxruntime as ort

        providers = tuple(ort.get_available_providers())
        if DIRECTML_PROVIDER not in providers:
            joined = ", ".join(providers) if providers else "none"
            raise RuntimeError(f"DirectML provider unavailable. Available providers: {joined}")


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
    return (
        "Analyze the article below. Return JSON only, without Markdown fences. "
        "Do not invent facts. Keep the title short. Write the summary from the article only. "
        "Copy each key sentence exactly from the article text.\n\n"
        "Return this JSON shape:\n"
        "{\n"
        '  "suggested_title": "short article title",\n'
        '  "summary": "3 to 5 sentence summary",\n'
        '  "key_sentences": ["important sentence copied from the article"],\n'
        '  "reason": "brief explanation of why these points matter"\n'
        "}\n\n"
        f"Article:\n{article_text}"
    )
