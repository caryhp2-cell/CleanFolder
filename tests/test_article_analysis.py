from offline_npu_renamer.core.article_analysis import analyze_article_text
from offline_npu_renamer.core.models import ModelAssetStatus, NpuStatus, SuggestionStatus


def test_article_analysis_requires_model_and_npu_gate():
    result = analyze_article_text(
        text="This article should not be analyzed without the offline model gate.",
        model_status=ModelAssetStatus(False, "Missing bundled model", ()),
        npu_status=NpuStatus(True, "OpenVINOExecutionProvider", "ok", ("OpenVINOExecutionProvider",)),
    )

    assert result.status is SuggestionStatus.ERROR
    assert result.summary == ""
    assert "Missing bundled model" in result.reason


def test_article_analysis_returns_extractive_summary_and_title():
    text = (
        "Offline AI tools are useful when files cannot leave the device. "
        "A local NPU can run compact models with lower power than a CPU. "
        "The renamer app already validates bundled ONNX models before analysis. "
        "The new article feature should reuse the same offline model and NPU gate. "
        "Users should see a short summary, key sentences, and a suggested title."
    )

    result = analyze_article_text(
        text=text,
        model_status=ModelAssetStatus(True, "models ok", ("document-title-v1",)),
        npu_status=NpuStatus(True, "OpenVINOExecutionProvider", "ok", ("OpenVINOExecutionProvider",)),
        max_sentences=2,
    )

    assert result.status is SuggestionStatus.READY
    assert result.suggested_title == "Offline AI tools are useful when files cannot leave the device"
    assert len(result.key_sentences) == 2
    assert "offline model and NPU gate" in result.summary
