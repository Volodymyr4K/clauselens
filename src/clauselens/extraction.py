"""Clause extraction pipeline.

Strategy: split the contract into overlapping chunks sized for reliable
attention (long-context models accept 100k+ tokens, but recall on
needle-in-haystack extraction degrades well before that), ask the model for
verbatim quotes per clause type in JSON, then *ground* every quote: a quote
that cannot be located in the source text is dropped, not trusted. Grounding
is what makes citations honest — the model never gets to invent text.
"""

import re
from dataclasses import dataclass, field

from .clauses import CLAUSE_TYPES
from .llm import LLMClient, TransientLLMError

CHUNK_CHARS = 6000
OVERLAP_CHARS = 800

SYSTEM_PROMPT = """\
You are a meticulous legal contract analyst. You extract clauses from contract
excerpts by quoting them VERBATIM. You never paraphrase, never summarize, and
never quote text that is not present in the excerpt. If a clause type is not
present in the excerpt, you return an empty list for it."""

def _format_clause(c) -> str:
    line = f'- "{c.key}": {c.description}'
    return f"{line} Hint: {c.hint}" if c.hint else line


HEADER_CLAUSES = [c for c in CLAUSE_TYPES if c.header]
BODY_CLAUSES = [c for c in CLAUSE_TYPES if not c.header]

_BODY_CLAUSE_LIST = "\n".join(_format_clause(c) for c in BODY_CLAUSES)
_HEADER_CLAUSE_LIST = "\n".join(_format_clause(c) for c in HEADER_CLAUSES)

USER_PROMPT_TEMPLATE = """\
Below is an excerpt from a legal contract. For each clause type listed, find
all passages in THIS EXCERPT that match the clause description.

Clause types:
{clause_list}

Rules:
- Quote passages VERBATIM, character for character, from the excerpt.
- Quote the complete sentence(s) or list item containing the clause — not a
  fragment, and not a whole section.
- If nothing in the excerpt matches a clause type, return [] for it.
- Output ONLY a JSON object mapping every clause key to a list of quotes.

Contract excerpt:
---
{chunk}
---

JSON:"""

HEADER_PROMPT_TEMPLATE = """\
Below is the {where} of a legal contract. Extract the document metadata
listed, if present.

Metadata types:
{clause_list}

Rules:
- Quote VERBATIM, character for character, from the excerpt.
- Quote each item once; do not quote running-text references to the parties
  or to "this Agreement".
- If an item is not present in this excerpt, return [] for it.
- Output ONLY a JSON object mapping every metadata key to a list of quotes.

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
    failed_chunks: int       # chunks lost to unparseable output or dead endpoint
    total_chunks: int        # failed_chunks/total_chunks = recall caveat for the run


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
    """Two-phase extraction.

    Header phase: metadata clauses (title, parties, date) are asked only of
    the document head and tail — preamble and signature block is where CUAD
    annotates them, and asking every chunk floods precision with running-text
    references. Body phase: the remaining clause types over all chunks.
    """
    state = _ExtractionState(text=text, client=client)

    head = text[:CHUNK_CHARS]
    state.process(
        HEADER_PROMPT_TEMPLATE.format(
            where="beginning", clause_list=_HEADER_CLAUSE_LIST, chunk=head),
        chunk=head, offset=0, valid_keys={c.key for c in HEADER_CLAUSES})
    if len(text) > CHUNK_CHARS:
        tail_offset = len(text) - CHUNK_CHARS
        tail = text[tail_offset:]
        state.process(
            HEADER_PROMPT_TEMPLATE.format(
                where="end (signature pages)", clause_list=_HEADER_CLAUSE_LIST,
                chunk=tail),
            chunk=tail, offset=tail_offset, valid_keys={c.key for c in HEADER_CLAUSES})

    body_keys = {c.key for c in BODY_CLAUSES}
    for offset, chunk in chunk_text(text):
        state.process(
            USER_PROMPT_TEMPLATE.format(clause_list=_BODY_CLAUSE_LIST, chunk=chunk),
            chunk=chunk, offset=offset, valid_keys=body_keys)

    return ExtractionResult(
        spans=_dedupe(state.spans), dropped_ungrounded=state.dropped,
        failed_chunks=state.failed_chunks, total_chunks=state.total_chunks)


@dataclass
class _ExtractionState:
    text: str
    client: LLMClient
    spans: list[ExtractedSpan] = field(default_factory=list)
    dropped: int = 0
    failed_chunks: int = 0
    total_chunks: int = 0

    def process(self, prompt: str, chunk: str, offset: int, valid_keys: set[str]):
        self.total_chunks += 1
        try:
            raw = self.client.chat_json(SYSTEM_PROMPT, prompt)
        except (ValueError, TransientLLMError):
            # a dead chunk costs recall but must not kill the whole run;
            # the loss is reported, not swallowed
            self.failed_chunks += 1
            return
        for clause_key, quotes in raw.items():
            if clause_key not in valid_keys or not isinstance(quotes, list):
                continue
            for quote in quotes:
                if not isinstance(quote, str) or not quote.strip():
                    continue
                located = ground_quote(quote, chunk, offset)
                if located is None:
                    self.dropped += 1
                    continue
                start, end = located
                self.spans.append(
                    ExtractedSpan(clause_key, self.text[start:end], start, end))


def _dedupe(spans: list[ExtractedSpan]) -> list[ExtractedSpan]:
    """Merge duplicates from overlapping chunks (same clause, overlapping range)."""
    out: list[ExtractedSpan] = []
    for s in sorted(spans, key=lambda s: (s.clause, s.start, -(s.end - s.start))):
        prev = out[-1] if out and out[-1].clause == s.clause else None
        if prev and s.start < prev.end:  # overlaps previous span of same clause
            continue
        out.append(s)
    return out
