"""Lexical passage retrieval over a single contract.

A contract can run to 300k characters — past the point where stuffing the
whole thing into the prompt keeps answer quality high. We split it into
overlapping passages and rank them per question with BM25.

BM25 (not vector search) on purpose: it needs no embedding model, is
deterministic, runs in milliseconds, and is a strong baseline on the keyword-
heavy language of contracts ("indemnification", "governing law"). A dense or
hybrid retriever can be added behind the same `Retriever` interface later;
that is a documented extension, not a prerequisite for working Q&A.
"""

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

PASSAGE_CHARS = 1000
PASSAGE_OVERLAP = 200
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Passage:
    text: str
    start: int  # char offset in the full contract
    end: int


def split_passages(
    text: str, size: int = PASSAGE_CHARS, overlap: int = PASSAGE_OVERLAP
) -> list[Passage]:
    if len(text) <= size:
        return [Passage(text, 0, len(text))]
    passages = []
    step = size - overlap
    for offset in range(0, len(text), step):
        chunk = text[offset:offset + size]
        passages.append(Passage(chunk, offset, offset + len(chunk)))
        if offset + size >= len(text):
            break
    return passages


class Retriever:
    """BM25 over the passages of one contract."""

    def __init__(self, text: str):
        self.passages = split_passages(text)
        self._bm25 = BM25Okapi([tokenize(p.text) for p in self.passages])

    def top_k(self, question: str, k: int = 6) -> list[Passage]:
        scores = self._bm25.get_scores(tokenize(question))
        ranked = sorted(
            range(len(self.passages)), key=lambda i: scores[i], reverse=True)
        return [self.passages[i] for i in ranked[:k]]
