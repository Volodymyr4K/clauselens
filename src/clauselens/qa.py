"""Question answering over a contract, with grounded citations.

The model answers using retrieved passages and must support every claim with
a verbatim quote. Each quote is grounded back into the passages it was drawn
from: a quote that cannot be located is dropped, exactly as in extraction. An
answer whose citations all fail to ground is flagged unsupported rather than
shown as if it were backed by the document.
"""

from dataclasses import dataclass, field

from .extraction import ground_quote
from .llm import LLMClient, TransientLLMError
from .retrieval import Passage, Retriever

SYSTEM_PROMPT = """\
You are a contract analyst. You answer questions about a contract using only
the provided passages. You never rely on outside knowledge, and you support
every factual claim with a verbatim quote from the passages. If the passages
do not contain the answer, you say so plainly."""

USER_PROMPT_TEMPLATE = """\
Answer the question using ONLY the passages below.

Question: {question}

Passages:
{passages}

Respond with a JSON object:
{{
  "answer": "<concise answer, or 'Not addressed in the contract.' if absent>",
  "citations": ["<verbatim quote from a passage>", ...]
}}
- Each citation MUST be copied character-for-character from a passage.
- Include a citation for every claim in the answer. Use [] only when the
  answer is that the contract does not address the question.

JSON:"""


@dataclass
class Citation:
    text: str   # grounded verbatim text from the contract
    start: int
    end: int


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    # the model produced an answer but none of its quotes could be grounded —
    # treat as unsupported, do not present as document-backed
    unsupported: bool = False
    retrieval_failed: bool = False  # the endpoint died; answer is empty


def _format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{i + 1}] {p.text}" for i, p in enumerate(passages))


def _ground_citation(quote: str, passages: list[Passage]) -> Citation | None:
    """Locate a quote within the passages the model was shown.

    Grounding inside the retrieved passages (not the whole contract) keeps the
    citation offset tied to the evidence the model actually used and sidesteps
    the multiple-identical-occurrence problem.
    """
    for p in passages:
        located = ground_quote(quote, p.text, p.start)
        if located is not None:
            start, end = located
            return Citation(p.text[start - p.start:end - p.start], start, end)
    return None


def answer_question(
    text: str, question: str, client: LLMClient, k: int = 6
) -> Answer:
    passages = Retriever(text).top_k(question, k=k)
    prompt = USER_PROMPT_TEMPLATE.format(
        question=question, passages=_format_passages(passages))
    try:
        raw = client.chat_json(SYSTEM_PROMPT, prompt)
    except (ValueError, TransientLLMError):
        return Answer(text="", retrieval_failed=True)

    answer_text = str(raw.get("answer", "")).strip()
    quotes = raw.get("citations", [])
    citations: list[Citation] = []
    if isinstance(quotes, list):
        for q in quotes:
            if not isinstance(q, str) or not q.strip():
                continue
            grounded = _ground_citation(q, passages)
            if grounded is not None:
                citations.append(grounded)

    # the model claimed support (non-empty citations) but none grounded
    unsupported = bool(quotes) and not citations
    return Answer(text=answer_text, citations=citations, unsupported=unsupported)
