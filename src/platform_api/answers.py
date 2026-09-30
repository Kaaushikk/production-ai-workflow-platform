import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from platform_api.search_service import RetrievedChunk

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "reveal your instructions",
)


@dataclass(frozen=True)
class GeneratedAnswer:
    text: str
    cited_chunk_ids: list[str]
    abstained: bool
    excluded_chunk_count: int


class AnswerProvider(ABC):
    name: str

    @abstractmethod
    def answer(self, question: str, evidence: list[RetrievedChunk]) -> GeneratedAnswer:
        """Answer using only supplied evidence and return the cited chunk IDs."""


def contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


class ExtractiveAnswerProvider(AnswerProvider):
    """Offline baseline that quotes relevant source sentences without generation."""

    name = "extractive-baseline-v1"

    def answer(self, question: str, evidence: list[RetrievedChunk]) -> GeneratedAnswer:
        question_terms = set(TOKEN_PATTERN.findall(question.lower()))
        safe = [item for item in evidence if not contains_prompt_injection(item.text)]
        excluded_count = len(evidence) - len(safe)
        selected: list[tuple[str, str]] = []
        for item in safe:
            sentences = SENTENCE_PATTERN.split(item.text)
            for sentence in sentences:
                sentence_terms = set(TOKEN_PATTERN.findall(sentence.lower()))
                if question_terms & sentence_terms:
                    selected.append((sentence.strip(), str(item.chunk_id)))
                    break
            if len(selected) == 3:
                break
        if not selected:
            return GeneratedAnswer(
                text="I could not find sufficient supporting evidence in the available documents.",
                cited_chunk_ids=[],
                abstained=True,
                excluded_chunk_count=excluded_count,
            )
        statements = [f"{sentence} [{index}]" for index, (sentence, _) in enumerate(selected, 1)]
        return GeneratedAnswer(
            text=" ".join(statements),
            cited_chunk_ids=[chunk_id for _, chunk_id in selected],
            abstained=False,
            excluded_chunk_count=excluded_count,
        )


default_answer_provider = ExtractiveAnswerProvider()

