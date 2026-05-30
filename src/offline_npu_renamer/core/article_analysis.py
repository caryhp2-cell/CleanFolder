from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from offline_npu_renamer.core.models import ModelAssetStatus, NpuStatus, SuggestionStatus

WORD_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。！？])\s+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "before",
    "can",
    "for",
    "is",
    "of",
    "or",
    "should",
    "the",
    "to",
    "when",
    "with",
}
DOMAIN_KEYWORDS = {"analysis", "article", "bundled", "feature", "gate", "model", "npu", "offline", "summary"}


@dataclass(frozen=True)
class ArticleAnalysisResult:
    suggested_title: str
    summary: str
    key_sentences: tuple[str, ...]
    reason: str
    status: SuggestionStatus


def analyze_article_text(
    text: str,
    model_status: ModelAssetStatus,
    npu_status: NpuStatus,
    max_sentences: int = 3,
) -> ArticleAnalysisResult:
    if not model_status.available:
        return _blocked(model_status.message)
    if not npu_status.available:
        return _blocked(npu_status.message)

    sentences = _split_sentences(text)
    if not sentences:
        return ArticleAnalysisResult(
            suggested_title="",
            summary="",
            key_sentences=(),
            reason="No article text was found.",
            status=SuggestionStatus.ERROR,
        )

    scores = _score_sentences(sentences)
    selected = sorted(
        sorted(range(len(sentences)), key=lambda index: scores[index], reverse=True)[:max_sentences]
    )
    key_sentences = tuple(sentences[index] for index in selected)
    return ArticleAnalysisResult(
        suggested_title=_suggest_title(sentences[0]),
        summary=" ".join(key_sentences),
        key_sentences=key_sentences,
        reason="Generated offline extractive summary using the bundled document model gate.",
        status=SuggestionStatus.READY,
    )


def _blocked(reason: str) -> ArticleAnalysisResult:
    return ArticleAnalysisResult(
        suggested_title="",
        summary="",
        key_sentences=(),
        reason=reason,
        status=SuggestionStatus.ERROR,
    )


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [sentence.strip().rstrip(".。") for sentence in SENTENCE_SPLIT_PATTERN.split(normalized) if sentence.strip()]


def _score_sentences(sentences: list[str]) -> list[float]:
    words_by_sentence = [_words(sentence) for sentence in sentences]
    frequencies = Counter(word for words in words_by_sentence for word in words)
    scores: list[float] = []
    for index, words in enumerate(words_by_sentence):
        if not words:
            scores.append(0.0)
            continue
        score = sum(frequencies[word] for word in words) / len(words)
        score += sum(0.7 for word in words if word in DOMAIN_KEYWORDS)
        if index == 0:
            score += 0.2
        scores.append(score)
    return scores


def _words(sentence: str) -> list[str]:
    return [
        word.lower()
        for word in WORD_PATTERN.findall(sentence)
        if len(word) > 2 and word.lower() not in STOP_WORDS
    ]


def _suggest_title(first_sentence: str, max_length: int = 72) -> str:
    title = first_sentence.strip().rstrip(".。")
    return title[:max_length].rstrip()
