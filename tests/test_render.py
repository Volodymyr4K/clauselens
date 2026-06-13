from clauselens.render import Highlight, _resolve_overlaps, render_highlighted


class TestResolveOverlaps:
    def test_disjoint_kept(self):
        hs = [Highlight(0, 5, "a"), Highlight(10, 15, "b")]
        assert len(_resolve_overlaps(hs)) == 2

    def test_overlap_drops_later(self):
        hs = [Highlight(0, 10, "a"), Highlight(5, 15, "b")]
        out = _resolve_overlaps(hs)
        assert len(out) == 1
        assert out[0].label == "a"

    def test_tie_prefers_longer(self):
        hs = [Highlight(0, 5, "short"), Highlight(0, 12, "long")]
        out = _resolve_overlaps(hs)
        assert len(out) == 1
        assert out[0].label == "long"


class TestRenderHighlighted:
    def test_wraps_span_in_mark(self):
        out = render_highlighted("abcDEFghi", [Highlight(3, 6, "x")])
        assert out == (
            'abc<mark class="clause" id="span-3" data-clause="x" '
            'data-start="3" title="x">DEF</mark>ghi')

    def test_escapes_contract_text(self):
        out = render_highlighted("a <script> b", [])
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_escapes_inside_mark(self):
        out = render_highlighted("x<i>y", [Highlight(1, 4, "c")])
        assert "<i>" not in out
        assert "&lt;i&gt;" in out

    def test_no_highlights_returns_escaped_text(self):
        assert render_highlighted("plain", []) == "plain"

    def test_offsets_preserved_across_multiple_marks(self):
        out = render_highlighted(
            "AAbbCCdd", [Highlight(0, 2, "p"), Highlight(4, 6, "q")])
        assert out == (
            '<mark class="clause" id="span-0" data-clause="p" data-start="0" '
            'title="p">AA</mark>'
            'bb<mark class="clause" id="span-4" data-clause="q" data-start="4" '
            'title="q">CC</mark>dd')
