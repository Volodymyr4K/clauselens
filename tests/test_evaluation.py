from clauselens.dataset import Contract, GoldSpan
from clauselens.evaluation import ClauseCounts, aggregate, char_iou, match_contract
from clauselens.extraction import ExtractedSpan


def make_contract(gold):
    return Contract(title="t", text="x" * 1000, gold=gold)


class TestCharIou:
    def test_identical(self):
        assert char_iou(10, 20, 10, 20) == 1.0

    def test_disjoint(self):
        assert char_iou(0, 10, 20, 30) == 0.0

    def test_half_overlap(self):
        # [0,10) vs [5,15): inter 5, union 15
        assert abs(char_iou(0, 10, 5, 15) - 5 / 15) < 1e-9

    def test_containment(self):
        # pred [0,100) contains gold [40,60): inter 20, union 100
        assert abs(char_iou(0, 100, 40, 60) - 0.2) < 1e-9


class TestMatchContract:
    def test_exact_match_is_tp(self):
        contract = make_contract({"governing_law": [GoldSpan("x" * 20, 100)]})
        preds = [ExtractedSpan("governing_law", "x" * 20, 100, 120)]
        counts, _ = match_contract(preds, contract)
        c = counts["governing_law"]
        assert (c.tp, c.fp, c.fn) == (1, 0, 0)

    def test_wider_quote_still_matches(self):
        # model quotes the enclosing sentence: gold 30 chars inside pred 80
        contract = make_contract({"exclusivity": [GoldSpan("x" * 30, 120)]})
        preds = [ExtractedSpan("exclusivity", "x" * 80, 100, 180)]
        counts, _ = match_contract(preds, contract)
        assert counts["exclusivity"].tp == 1  # IoU 30/80 = 0.375 >= 0.3

    def test_miss_is_fn_and_stray_is_fp(self):
        contract = make_contract({"non_compete": [GoldSpan("x" * 20, 100)]})
        preds = [ExtractedSpan("non_compete", "y" * 20, 700, 720)]
        counts, _ = match_contract(preds, contract)
        c = counts["non_compete"]
        assert (c.tp, c.fp, c.fn) == (0, 1, 1)

    def test_gold_matched_at_most_once(self):
        contract = make_contract({"parties": [GoldSpan("x" * 20, 100)]})
        preds = [
            ExtractedSpan("parties", "x" * 20, 100, 120),
            ExtractedSpan("parties", "x" * 18, 101, 119),
        ]
        counts, _ = match_contract(preds, contract)
        c = counts["parties"]
        assert (c.tp, c.fp) == (1, 1)

    def test_absent_clause_correctly_silent(self):
        contract = make_contract({"audit_rights": []})
        _, absence = match_contract([], contract)
        assert absence["audit_rights"] is True

    def test_absent_clause_false_alarm(self):
        contract = make_contract({"audit_rights": []})
        preds = [ExtractedSpan("audit_rights", "x" * 10, 0, 10)]
        counts, absence = match_contract(preds, contract)
        assert absence["audit_rights"] is False
        assert counts["audit_rights"].fp == 1


class TestTextMatch:
    def test_identical_string_different_offset_is_tp(self):
        # gold title at offset 500; model quoted the same title grounded at 16
        contract = make_contract({"document_name": [GoldSpan("SUPPLY AGREEMENT", 500)]})
        preds = [ExtractedSpan("document_name", "SUPPLY AGREEMENT", 16, 32)]
        counts, _ = match_contract(preds, contract)
        c = counts["document_name"]
        assert (c.tp, c.fp, c.fn) == (1, 0, 0)

    def test_case_and_whitespace_normalized(self):
        contract = make_contract(
            {"document_name": [GoldSpan("Distributor Agreement", 500)]})
        preds = [ExtractedSpan("document_name", "DISTRIBUTOR  AGREEMENT", 16, 38)]
        counts, _ = match_contract(preds, contract)
        assert counts["document_name"].tp == 1

    def test_text_match_disabled_keeps_strict(self):
        contract = make_contract({"document_name": [GoldSpan("SUPPLY AGREEMENT", 500)]})
        preds = [ExtractedSpan("document_name", "SUPPLY AGREEMENT", 16, 32)]
        counts, _ = match_contract(preds, contract, text_match=False)
        c = counts["document_name"]
        assert (c.tp, c.fp, c.fn) == (0, 1, 1)  # offsets disagree -> miss

    def test_text_match_does_not_admit_unrelated_text(self):
        contract = make_contract({"document_name": [GoldSpan("SUPPLY AGREEMENT", 500)]})
        preds = [ExtractedSpan("document_name", "this Agreement", 16, 30)]
        counts, _ = match_contract(preds, contract)
        c = counts["document_name"]
        assert (c.tp, c.fp) == (0, 1)

    def test_positional_match_preferred_over_text(self):
        # two identical gold strings; a positionally-overlapping pred should
        # claim the overlapped one, leaving the other for a second pred
        contract = make_contract(
            {"parties": [GoldSpan("Company", 100), GoldSpan("Company", 900)]})
        preds = [
            ExtractedSpan("parties", "Company", 98, 105),   # overlaps gold@100
            ExtractedSpan("parties", "Company", 500, 507),  # text-matches gold@900
        ]
        counts, _ = match_contract(preds, contract)
        c = counts["parties"]
        assert (c.tp, c.fp, c.fn) == (2, 0, 0)


class TestAggregate:
    def test_sums_and_specificity(self):
        c1 = {"exclusivity": ClauseCounts(tp=2, fp=1, fn=0)}
        c2 = {"exclusivity": ClauseCounts(tp=1, fp=0, fn=2)}
        report = aggregate([(c1, {"non_compete": True}), (c2, {"non_compete": False})])
        e = report.per_clause["exclusivity"]
        assert (e.tp, e.fp, e.fn) == (3, 1, 2)
        assert report.absence["non_compete"].specificity == 0.5
