import json
import sys
from types import SimpleNamespace

from offline_npu_renamer.core.article_llm import PhiArticleGenerator


def test_phi_article_generator_uses_openvino_genai_gpu_pipeline(tmp_path, monkeypatch):
    model_dir = tmp_path / "openvino-phi"
    model_dir.mkdir()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "article-llm-phi35-mini-openvino-gpu-v1",
                        "path": "openvino-phi",
                        "task": "article-llm-analysis",
                        "required_provider": "GPU",
                        "required_files": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, str]] = []

    class FakePipeline:
        def __init__(self, path: str, device: str) -> None:
            calls.append((path, device))

        def generate(self, prompt: str, max_new_tokens: int) -> str:
            assert "Return JSON only" in prompt
            assert "summary <= 80 characters" in prompt
            assert "reason <= 40 characters" in prompt
            assert "exactly 2 key_sentences" in prompt
            assert max_new_tokens == 123
            return '{"suggested_title":"ok","summary":"ok","key_sentences":["ok"],"reason":"ok"}'

    fake_genai = SimpleNamespace(LLMPipeline=FakePipeline)
    monkeypatch.setitem(sys.modules, "openvino_genai", fake_genai)

    output = PhiArticleGenerator(
        models_dir=tmp_path,
        max_new_tokens=123,
    ).generate("OpenVINO GenAI can run optimized language models on Intel integrated GPUs.")

    assert '"suggested_title":"ok"' in output
    assert calls == [(str(model_dir), "GPU")]
