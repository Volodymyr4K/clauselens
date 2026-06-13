"""Turn a contract plus spans into highlighted HTML — pure, no I/O.

Kept separate from the web layer so the highlighting logic (the fiddly part:
overlaps, escaping, offset bookkeeping) is unit-tested without a server.
"""

import html
from dataclasses import dataclass


@dataclass
class Highlight:
    start: int
    end: int
    label: str   # clause key, used for color + tooltip


def _resolve_overlaps(highlights: list[Highlight]) -> list[Highlight]:
    """Drop overlaps so the rendered markup stays well-formed.

    Earlier start wins; ties go to the longer span. A later span that overlaps
    an already-placed one is skipped (the clause is still listed in the
    sidebar, just not double-marked in the text).
    """
    out: list[Highlight] = []
    last_end = -1
    for h in sorted(highlights, key=lambda h: (h.start, -(h.end - h.start))):
        if h.start >= last_end and h.end > h.start:
            out.append(h)
            last_end = h.end
    return out


def render_highlighted(text: str, highlights: list[Highlight]) -> str:
    """Return HTML with <mark> wrapping each highlight, everything escaped.

    The whole text is HTML-escaped; marks are inserted at the right offsets so
    nothing in the contract can inject markup.
    """
    spans = _resolve_overlaps(highlights)
    pieces: list[str] = []
    cursor = 0
    for h in spans:
        if h.start > cursor:
            pieces.append(html.escape(text[cursor:h.start]))
        marked = html.escape(text[h.start:h.end])
        pieces.append(
            f'<mark class="clause" id="span-{h.start}" '
            f'data-clause="{html.escape(h.label)}" data-start="{h.start}" '
            f'title="{html.escape(h.label)}">{marked}</mark>')
        cursor = h.end
    if cursor < len(text):
        pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)
