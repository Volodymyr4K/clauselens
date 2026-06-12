"""Span-level evaluation against CUAD gold annotations.

A predicted span matches a gold span of the same clause type when their
character-range IoU (intersection over union) clears a threshold. Greedy
one-to-one matching: each gold span can be claimed by at most one prediction.

Threshold choice (documented, not hidden): 0.3. Lawyers annotate minimal
passages while LLMs tend to quote the enclosing sentence; demanding IoU 0.5+
punishes a prediction that fully contains the gold answer with extra context.
At 0.3 a prediction still has to land on the right passage — random text
nearby will not clear it. Sensitivity to this threshold is reported by the
eval script rather than asserted away.
"""

from dataclasses import dataclass, field

from .dataset import Contract, GoldSpan
from .extraction import ExtractedSpan

IOU_THRESHOLD = 0.3


def char_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union else 0.0


@dataclass
class ClauseCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class AbsenceCounts:
    """Did the system correctly say 'this clause is absent'?

    Half the value for a reviewer: a system that finds clauses but cries wolf
    on absent ones is useless. Counted per (contract, clause type) pair where
    gold has no spans.
    """
    true_absent: int = 0   # gold absent, predicted absent
    false_found: int = 0   # gold absent, system predicted something

    @property
    def specificity(self) -> float:
        total = self.true_absent + self.false_found
        return self.true_absent / total if total else 0.0


@dataclass
class EvalReport:
    per_clause: dict[str, ClauseCounts] = field(default_factory=dict)
    absence: dict[str, AbsenceCounts] = field(default_factory=dict)

    def micro(self) -> ClauseCounts:
        total = ClauseCounts()
        for c in self.per_clause.values():
            total.tp += c.tp
            total.fp += c.fp
            total.fn += c.fn
        return total

    def macro_f1(self) -> float:
        if not self.per_clause:
            return 0.0
        return sum(c.f1 for c in self.per_clause.values()) / len(self.per_clause)


def match_contract(
    predicted: list[ExtractedSpan],
    contract: Contract,
    iou_threshold: float = IOU_THRESHOLD,
) -> tuple[dict[str, ClauseCounts], dict[str, bool]]:
    """Greedy IoU matching for one contract.

    Returns per-clause counts and, for clause types with no gold spans,
    whether the system also predicted nothing (absence map).
    """
    counts: dict[str, ClauseCounts] = {}
    absence: dict[str, bool] = {}
    preds_by_clause: dict[str, list[ExtractedSpan]] = {}
    for p in predicted:
        preds_by_clause.setdefault(p.clause, []).append(p)

    for clause, gold_spans in contract.gold.items():
        preds = preds_by_clause.get(clause, [])
        if not gold_spans:
            absence[clause] = not preds
            # predictions against empty gold are false positives
            if preds:
                counts.setdefault(clause, ClauseCounts()).fp += len(preds)
            continue
        c = counts.setdefault(clause, ClauseCounts())
        unmatched_gold = list(_gold_ranges(gold_spans))
        for p in sorted(preds, key=lambda p: p.start):
            best_i, best_iou = -1, 0.0
            for i, (gs, ge) in enumerate(unmatched_gold):
                iou = char_iou(p.start, p.end, gs, ge)
                if iou > best_iou:
                    best_i, best_iou = i, iou
            if best_iou >= iou_threshold:
                c.tp += 1
                unmatched_gold.pop(best_i)
            else:
                c.fp += 1
        c.fn += len(unmatched_gold)
    return counts, absence


def _gold_ranges(gold_spans: list[GoldSpan]):
    for g in gold_spans:
        yield g.start, g.start + len(g.text)


def aggregate(
    results: list[tuple[dict[str, ClauseCounts], dict[str, bool]]],
) -> EvalReport:
    report = EvalReport()
    for counts, absence in results:
        for clause, c in counts.items():
            agg = report.per_clause.setdefault(clause, ClauseCounts())
            agg.tp += c.tp
            agg.fp += c.fp
            agg.fn += c.fn
        for clause, correctly_absent in absence.items():
            a = report.absence.setdefault(clause, AbsenceCounts())
            if correctly_absent:
                a.true_absent += 1
            else:
                a.false_found += 1
    return report
