from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from offline_npu_renamer.core.models import SuggestionStatus

ArticleGenerator = Callable[[str], str]


@dataclass(frozen=True)
class ArticleAnalysisResult:
    suggested_title: str
    summary: str
    key_sentences: tuple[str, ...]
    reason: str
    status: SuggestionStatus


def analyze_article_text(
    text: str,
    generator: ArticleGenerator | None = None,
) -> ArticleAnalysisResult:
    article_text = " ".join(text.split())
    if not article_text:
        return _blocked("No article text was found.")

    active_generator = generator or _default_generator
    try:
        raw_output = active_generator(article_text)
    except Exception as error:
        return _blocked(f"Article LLM generation failed: {error}")

    try:
        payload = json.loads(_strip_markdown_fences(raw_output))
    except json.JSONDecodeError:
        return _blocked("Article LLM output was not valid JSON.")

    return _validate_payload(payload, article_text)


def _default_generator(text: str) -> str:
    from offline_npu_renamer.core.article_llm import PhiArticleGenerator

    return PhiArticleGenerator().generate(text)


def _validate_payload(payload: Any, article_text: str) -> ArticleAnalysisResult:
    if not isinstance(payload, dict):
        return _blocked("Article LLM output must be a JSON object.")

    title = _required_string(payload, "suggested_title")
    if title is None:
        return _blocked("Article LLM output is missing suggested_title.")

    summary = _required_string(payload, "summary")
    if summary is None:
        return _blocked("Article LLM output is missing summary.")

    key_sentences = payload.get("key_sentences")
    if not isinstance(key_sentences, list) or not key_sentences:
        return _blocked("Article LLM output is missing key_sentences.")

    validated_sentences: list[str] = []
    for value in key_sentences:
        if not isinstance(value, str) or not value.strip():
            return _blocked("Article LLM key_sentences must contain non-empty strings.")
        sentence = value.strip()
        if not _sentence_matches_source(sentence, article_text):
            return _blocked(f"Article LLM key sentence was not found in the article: {sentence}")
        validated_sentences.append(sentence)

    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""

    return ArticleAnalysisResult(
        suggested_title=title,
        summary=summary,
        key_sentences=tuple(validated_sentences),
        reason=reason.strip(),
        status=SuggestionStatus.READY,
    )


def _required_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _sentence_matches_source(sentence: str, article_text: str) -> bool:
    normalized_sentence = _normalize_for_match(sentence)
    normalized_article = _normalize_for_match(article_text)
    if normalized_sentence in normalized_article:
        return True

    source_sentences = _split_sentences(article_text)
    return any(
        SequenceMatcher(None, normalized_sentence, _normalize_for_match(source)).ratio() >= 0.9
        for source in source_sentences
    )


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]


def _normalize_for_match(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip().rstrip(".。")


def _strip_markdown_fences(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _blocked(reason: str) -> ArticleAnalysisResult:
    return ArticleAnalysisResult(
        suggested_title="",
        summary="",
        key_sentences=(),
        reason=reason,
        status=SuggestionStatus.ERROR,
    )
