"""Clause extraction pipeline.

Strategy: split the contract into overlapping chunks sized for reliable
attention (long-context models accept 100k+ tokens, but recall on
needle-in-haystack extraction degrades well before that), ask the model for
verbatim quotes per clause type in JSON, then *ground* every quote: a quote
that cannot be located in the source text is dropped, not trusted. Grounding
is what makes citations honest — the model never gets to invent text.
"""

import re
from dataclasses import dataclass

from .clauses import CLAUSE_TYPES
from .llm import LLMClient

CHUNK_CHARS = 6000
OVERLAP_CHARS = 800

SYSTEM_PROMPT = """\
You are a meticulous legal contract analyst. You extract clauses from contract
excerpts by quoting them VERBATIM. You never paraphrase, never summarize, and
never quote text that is not present in the excerpt. If a clause type is not
present in the excerpt, you return an empty list for it."""

_CLAUSE_LIST = "\n".join(
    f'- "{c.key}": {c.description}' for c in CLAUSE_TYPES
)

USER_PROMPT_TEMPLATE = """\
Below is an excerpt from a legal contract. For each clause type listed, find
all passages in THIS EXCERPT that match the clause description.

Clause types:
{clause_list}

Rules:
- Quote passages VERBATIM, character for character, from the excerpt.
- A quote should be the minimal self-contained passage (typically one sentence
  or list item), not a whole section.
- If nothing in the excerpt matches a clause type, return [] for it.
- Output ONLY a JSON object mapping every clause key to a list of quotes.

Contract excerpt:
---
{chunk}
---

JSON:"""


@dataclass
class ExtractedSpan:
    clause: str   # clause key
    text: str     # grounded verbatim text (as it appears in the contract)
    start: int    # char offset in the full contract text
    end: int


@dataclass
class ExtractionResult:
    spans: list[ExtractedSpan]
    dropped_ungrounded: int  # quotes the model produced but we could not locate


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS):
    """Yield (offset, chunk) pairs covering the text with overlap."""
    if len(text) <= size:
        yield 0, text
        return
    step = size - overlap
    for offset in range(0, len(text), step):
        yield offset, text[offset:offset + size]
        if offset + size >= len(text):
            break


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def ground_quote(quote: str, chunk: str, chunk_offset: int) -> tuple[int, int] | None:
    """Locate a model quote in the source chunk; return absolute (start, end).

    Exact match first; then a whitespace-insensitive search, since models
    routinely collapse line breaks inside otherwise-verbatim quotes.
    """
    idx = chunk.find(quote)
    if idx != -1:
        return chunk_offset + idx, chunk_offset + idx + len(quote)

    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    if not pattern:
        return None
    m = re.search(pattern, chunk, re.IGNORECASE)
    if m:
        return chunk_offset + m.start(), chunk_offset + m.end()
    return None


def extract_clauses(text: str, client: LLMClient) -> ExtractionResult:
    spans: list[ExtractedSpan] = []
    dropped = 0
    for offset, chunk in chunk_text(text):
        prompt = USER_PROMPT_TEMPLATE.format(clause_list=_CLAUSE_LIST, chunk=chunk)
        try:
            raw = client.chat_json(SYSTEM_PROMPT, prompt)
        except ValueError:
            dropped += 1  # count the whole chunk as a failure signal
            continue
        for clause_key, quotes in raw.items():
            if clause_key not in {c.key for c in CLAUSE_TYPES}:
                continue
            if not isinstance(quotes, list):
                continue
            for quote in quotes:
                if not isinstance(quote, str) or not quote.strip():
                    continue
                located = ground_quote(quote, chunk, offset)
                if located is None:
                    dropped += 1
                    continue
                start, end = located
                spans.append(ExtractedSpan(clause_key, text[start:end], start, end))
    return ExtractionResult(spans=_dedupe(spans), dropped_ungrounded=dropped)


def _dedupe(spans: list[ExtractedSpan]) -> list[ExtractedSpan]:
    """Merge duplicates from overlapping chunks (same clause, overlapping range)."""
    out: list[ExtractedSpan] = []
    for s in sorted(spans, key=lambda s: (s.clause, s.start, -(s.end - s.start))):
        prev = out[-1] if out and out[-1].clause == s.clause else None
        if prev and s.start < prev.end:  # overlaps previous span of same clause
            continue
        out.append(s)
    return out
