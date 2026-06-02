import json

from offline_npu_renamer.core.article_analysis import analyze_article_text
from offline_npu_renamer.core.models import SuggestionStatus


ARTICLE_TEXT = (
    "Offline tools are useful when private files cannot leave the device. "
    "DirectML can accelerate local language model generation on Windows GPUs. "
    "The article analyzer should return a short title, summary, and copied key sentences."
)


def test_article_analysis_accepts_valid_llm_json():
    def generator(text: str) -> str:
        assert "Offline tools are useful" in text
        return json.dumps(
            {
                "suggested_title": "Local Article Analysis",
                "summary": "The article explains why local analysis helps private files.",
                "key_sentences": [
                    "Offline tools are useful when private files cannot leave the device.",
                    "DirectML can accelerate local language model generation on Windows GPUs.",
                ],
                "reason": "These sentences capture privacy and performance.",
            }
        )

    result = analyze_article_text(ARTICLE_TEXT, generator=generator)

    assert result.status is SuggestionStatus.READY
    assert result.suggested_title == "Local Article Analysis"
    assert "private files" in result.summary
    assert len(result.key_sentences) == 2
    assert "privacy" in result.reason


def test_article_analysis_rejects_invalid_json():
    result = analyze_article_text(ARTICLE_TEXT, generator=lambda _: "not-json")

    assert result.status is SuggestionStatus.ERROR
    assert result.summary == ""
    assert "valid JSON" in result.reason


def test_article_analysis_accepts_first_json_object_before_extra_text():
    def generator(_: str) -> str:
        return (
            '{"suggested_title":"Local Article Analysis",'
            '"summary":"The article explains local analysis.",'
            '"key_sentences":["Offline tools are useful when private files cannot leave the device."],'
            '"reason":"privacy"}'
            "\n\nExtra text that the model should not have emitted."
        )

    result = analyze_article_text(ARTICLE_TEXT, generator=generator)

    assert result.status is SuggestionStatus.READY
    assert result.suggested_title == "Local Article Analysis"


def test_article_analysis_repairs_llm_output_with_only_key_sentences():
    def generator(_: str) -> str:
        return (
            '{"key_sentences":['
            '"Offline tools are useful when private files cannot leave the device.",'
            '"DirectML can accelerate local language model generation on Windows GPUs."'
            "]}\n\nReason: The model selected the most relevant sentences."
        )

    result = analyze_article_text(ARTICLE_TEXT, generator=generator)

    assert result.status is SuggestionStatus.READY
    assert result.suggested_title == "Offline tools are useful when private files cannot leave the device"
    assert result.summary == (
        "Offline tools are useful when private files cannot leave the device. "
        "DirectML can accelerate local language model generation on Windows GPUs."
    )
    assert len(result.key_sentences) == 2


def test_article_analysis_rejects_hallucinated_key_sentences():
    def generator(_: str) -> str:
        return json.dumps(
            {
                "suggested_title": "Local Article Analysis",
                "summary": "The article explains local analysis.",
                "key_sentences": ["The cloud service stores every article permanently."],
                "reason": "The sentence is important.",
            }
        )

    result = analyze_article_text(ARTICLE_TEXT, generator=generator)

    assert result.status is SuggestionStatus.ERROR
    assert "not found in the article" in result.reason


def test_article_analysis_rejects_empty_text_before_generation():
    called = False

    def generator(_: str) -> str:
        nonlocal called
        called = True
        return "{}"

    result = analyze_article_text("  \n\t", generator=generator)

    assert result.status is SuggestionStatus.ERROR
    assert result.reason == "No article text was found."
    assert called is False


def test_article_analysis_reports_generator_failure():
    def generator(_: str) -> str:
        raise RuntimeError("DirectML provider unavailable")

    result = analyze_article_text(ARTICLE_TEXT, generator=generator)

    assert result.status is SuggestionStatus.ERROR
    assert "DirectML provider unavailable" in result.reason
