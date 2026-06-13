from types import SimpleNamespace
from unittest.mock import patch

from clauselens.qa import _ground_citation, answer_question
from clauselens.retrieval import Retriever, split_passages, tokenize


class TestRetrieval:
    def test_short_text_single_passage(self):
        passages = split_passages("a short contract")
        assert len(passages) == 1
        assert (passages[0].start, passages[0].end) == (0, 16)

    def test_passages_carry_absolute_offsets(self):
        text = "ABCDE" * 600  # 3000 chars
        passages = split_passages(text, size=1000, overlap=200)
        for p in passages:
            assert text[p.start:p.end] == p.text

    def test_bm25_ranks_relevant_passage_first(self):
        text = (
            "The widget shall be blue. " * 40
            + "This Agreement is governed by the laws of Delaware. " * 5
            + "The widget shall be blue. " * 40
        )
        top = Retriever(text).top_k("Which law governs the agreement?", k=1)
        assert "Delaware" in top[0].text

    def test_tokenize_lowercases_and_splits(self):
        assert tokenize("Governing-Law, Delaware!") == ["governing", "law", "delaware"]


class TestGroundCitation:
    def test_grounds_within_passage_with_absolute_offset(self):
        passages = split_passages("x" * 500 + "governed by Delaware law", size=1000)
        cit = _ground_citation("governed by Delaware", passages)
        assert cit is not None
        assert cit.start == 500
        assert cit.text == "governed by Delaware"

    def test_ungrounded_quote_returns_none(self):
        passages = split_passages("totally unrelated contract text")
        assert _ground_citation("liability is uncapped", passages) is None


def mock_client(payload):
    client = SimpleNamespace()
    client.chat_json = lambda system, user, retries=2: payload
    return client


class TestAnswerQuestion:
    @patch("clauselens.qa.Retriever")
    def test_grounded_citation_kept(self, MockRetriever):
        from clauselens.retrieval import Passage
        MockRetriever.return_value.top_k.return_value = [
            Passage("This Agreement is governed by Delaware law.", 100, 143)]
        client = mock_client(
            {"answer": "Delaware law governs.",
             "citations": ["governed by Delaware law"]})
        ans = answer_question("ignored", "governing law?", client)
        assert ans.text == "Delaware law governs."
        assert len(ans.citations) == 1
        assert ans.citations[0].start == 118  # 100 + len("This Agreement is ")
        assert not ans.unsupported

    @patch("clauselens.qa.Retriever")
    def test_hallucinated_citation_marks_unsupported(self, MockRetriever):
        from clauselens.retrieval import Passage
        MockRetriever.return_value.top_k.return_value = [
            Passage("This contract is about widgets.", 0, 31)]
        client = mock_client(
            {"answer": "Liability is uncapped.",
             "citations": ["liability shall be uncapped"]})
        ans = answer_question("ignored", "liability?", client)
        assert ans.unsupported
        assert ans.citations == []

    @patch("clauselens.qa.Retriever")
    def test_absent_answer_no_citations_not_unsupported(self, MockRetriever):
        from clauselens.retrieval import Passage
        MockRetriever.return_value.top_k.return_value = [Passage("text", 0, 4)]
        client = mock_client(
            {"answer": "Not addressed in the contract.", "citations": []})
        ans = answer_question("ignored", "arbitration?", client)
        assert not ans.unsupported
        assert ans.citations == []
