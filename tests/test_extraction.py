from clauselens.extraction import ExtractedSpan, _dedupe, chunk_text, ground_quote


class TestChunkText:
    def test_short_text_single_chunk(self):
        chunks = list(chunk_text("hello", size=100, overlap=10))
        assert chunks == [(0, "hello")]

    def test_chunks_cover_whole_text(self):
        text = "x" * 25000
        chunks = list(chunk_text(text, size=6000, overlap=800))
        covered_end = max(off + len(c) for off, c in chunks)
        assert covered_end == len(text)
        assert chunks[0][0] == 0

    def test_consecutive_chunks_overlap(self):
        text = "abcdefghij" * 2000
        chunks = list(chunk_text(text, size=6000, overlap=800))
        for (off1, c1), (off2, _) in zip(chunks, chunks[1:]):
            assert off2 < off1 + len(c1), "chunks must overlap"


class TestGroundQuote:
    def test_exact_match(self):
        chunk = "This Agreement shall be governed by the laws of Delaware."
        expected_start = 100 + chunk.find("laws of Delaware")
        assert ground_quote("laws of Delaware", chunk, 100) == (
            expected_start, expected_start + len("laws of Delaware"))

    def test_whitespace_insensitive_match(self):
        chunk = "governed by\n   the laws of Delaware"
        located = ground_quote("governed by the laws", chunk, 0)
        assert located is not None
        start, end = located
        assert chunk[start:end] == "governed by\n   the laws"

    def test_hallucinated_quote_rejected(self):
        assert ground_quote("liability is unlimited", "totally unrelated text", 0) is None

    def test_empty_quote_rejected(self):
        assert ground_quote("   ", "some text", 0) is None


class TestDedupe:
    def test_overlapping_same_clause_merged(self):
        spans = [
            ExtractedSpan("governing_law", "laws of Delaware", 100, 116),
            ExtractedSpan("governing_law", "the laws of Delaware", 96, 116),
        ]
        result = _dedupe(spans)
        assert len(result) == 1
        assert result[0].start == 96  # keeps the earliest-starting span

    def test_same_range_different_clause_kept(self):
        spans = [
            ExtractedSpan("governing_law", "text", 100, 116),
            ExtractedSpan("exclusivity", "text", 100, 116),
        ]
        assert len(_dedupe(spans)) == 2

    def test_disjoint_same_clause_kept(self):
        spans = [
            ExtractedSpan("license_grant", "grant a", 0, 10),
            ExtractedSpan("license_grant", "grant b", 500, 510),
        ]
        assert len(_dedupe(spans)) == 2
