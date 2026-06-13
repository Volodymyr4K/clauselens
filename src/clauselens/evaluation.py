"""Span-level evaluation against CUAD gold annotations.

A predicted span matches a gold span of the same clause type when EITHER:
  1. their character-range IoU clears a threshold (positional match), OR
  2. the prediction reproduces the gold span's text verbatim, case- and
     whitespace-normalized (text match).

Greedy one-to-one matching: each gold span can be claimed by at most one
prediction.

Why the text-match arm (2): CUAD's own evaluation is text-overlap retrieval,
not character-offset alignment. Some answers — most visibly the document
title — appear as the identical string at several offsets (an exhibit-header
caption and an inline title), while the annotators marked exactly one of them.
Pure offset IoU then scores a verbatim-correct answer as both a false positive
and a false negative. Reproducing a gold answer string verbatim is a true
positive by any reasonable reading, so it is counted as one. This arm is
strict: it requires near-equality of the answer text, not mere overlap, so it
cannot admit unrelated predictions.

Threshold choice for arm (1) (documented, not hidden): 0.3. Lawyers annotate
minimal passages while LLMs tend to quote the enclosing sentence; demanding
IoU 0.5+ punishes a prediction that fully contains the gold answer with extra
context. At 0.3 a prediction still has to land on the right passage. Both the
strict positional-only score and the combined score are reported, so the
effect of arm (2) is visible rather than buried.
"""

import re
from dataclasses import dataclass, field

from .dataset import Contract, GoldSpan
from .extraction import ExtractedSpan

IOU_THRESHOLD = 0.3


def char_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union else 0.0


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


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
    text_match: bool = True,
) -> tuple[dict[str, ClauseCounts], dict[str, bool]]:
    """Greedy matching for one contract.

    With text_match=True a prediction also matches a gold span whose text it
    reproduces verbatim (normalized), not only one it positionally overlaps.
    Set text_match=False for the strict positional-only score.

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
        unmatched = list(gold_spans)
        for p in sorted(preds, key=lambda p: p.start):
            idx = _best_gold(p, unmatched, iou_threshold, text_match)
            if idx is not None:
                c.tp += 1
                unmatched.pop(idx)
            else:
                c.fp += 1
        c.fn += len(unmatched)
    return counts, absence


def _best_gold(
    pred: ExtractedSpan,
    unmatched: list[GoldSpan],
    iou_threshold: float,
    text_match: bool,
) -> int | None:
    """Index of the gold span this prediction claims, or None.

    Prefers the strongest positional overlap; falls back to a verbatim text
    match (used for identical strings sitting at different offsets).
    """
    best_i, best_iou = None, iou_threshold
    for i, g in enumerate(unmatched):
        iou = char_iou(pred.start, pred.end, g.start, g.start + len(g.text))
        if iou >= best_iou:
            best_i, best_iou = i, iou
    if best_i is not None:
        return best_i
    if text_match:
        pred_norm = _norm(pred.text)
        for i, g in enumerate(unmatched):
            if _norm(g.text) == pred_norm:
                return i
    return None


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
