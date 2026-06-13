"""Evaluate the Q&A path's citations against CUAD gold spans. Resumable.

For each contract and clause type we ask the natural-language question and
check the answer's citations against the lawyer-annotated gold spans for that
clause. This measures whether Q&A points the user at the right passage —
reusing the same ground truth as extraction, so even the Q&A is evaluated
against expert annotation rather than vibes.

Two things are measured:
- Citation hit rate (clause present): did at least one citation land on a gold
  span (IoU >= 0.3 or verbatim text match)? This is answer-grounding recall.
- Absence handling (clause absent): did Q&A correctly return no grounded
  citation instead of inventing support?

Usage:
    uv run python scripts/run_qa_eval.py --run qa-gemma4-train10 -n 10
    uv run python scripts/run_qa_eval.py --run qa-gemma4-train10 --report-only
"""

import argparse
import json
import sys
import time
from pathlib import Path

from clauselens.clauses import QUESTIONS
from clauselens.dataset import DATA_DIR, load_contracts
from clauselens.evaluation import IOU_THRESHOLD, _norm, char_iou
from clauselens.llm import LLMClient
from clauselens.qa import answer_question

RUNS_DIR = Path(__file__).resolve().parents[1] / "eval_runs"


def select_contracts(split: str, n: int):
    if split == "test":
        contracts = load_contracts(DATA_DIR / "test.json")
    else:
        test_titles = {c.title for c in load_contracts(DATA_DIR / "test.json")}
        contracts = [c for c in load_contracts() if c.title not in test_titles]
    contracts.sort(key=lambda c: len(c.text))
    if n >= len(contracts):
        return contracts
    stride = len(contracts) / n
    return [contracts[int(i * stride)] for i in range(n)]


GOLD_COVERAGE = 0.5


def _gold_coverage(cit, g) -> float:
    """Fraction of the gold span's characters covered by the citation.

    The right question for a Q&A citation is "does the cited passage contain
    the answer", not "is it a tight span" — so coverage of the gold span, not
    IoU, is the natural criterion here.
    """
    gs, ge = g.start, g.start + len(g.text)
    inter = max(0, min(cit["end"], ge) - max(cit["start"], gs))
    return inter / (ge - gs) if ge > gs else 0.0


def citation_hits_gold(citations, gold_spans, strict: bool = False) -> bool:
    for c in citations:
        for g in gold_spans:
            if _norm(c["text"]) == _norm(g.text):
                return True
            if strict:
                gs, ge = g.start, g.start + len(g.text)
                if char_iou(c["start"], c["end"], gs, ge) >= IOU_THRESHOLD:
                    return True
            elif _gold_coverage(c, g) >= GOLD_COVERAGE:
                return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", choices=["train", "test"], default="train")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    run_dir = RUNS_DIR / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    ans_file = run_dir / "answers.jsonl"

    done: dict[tuple[str, str], dict] = {}
    if ans_file.exists():
        for line in ans_file.read_text().splitlines():
            rec = json.loads(line)
            done[(rec["title"], rec["clause"])] = rec

    contracts = select_contracts(args.split, args.n)

    if not args.report_only:
        client = LLMClient()
        (run_dir / "meta.json").write_text(json.dumps(
            {"model": client.model, "split": args.split, "n": args.n,
             "task": "qa_citation_eval"}, indent=2))
        with ans_file.open("a") as out:
            for ci, contract in enumerate(contracts):
                for clause, question in QUESTIONS.items():
                    if (contract.title, clause) in done:
                        continue
                    t0 = time.time()
                    ans = answer_question(contract.text, question, client)
                    rec = {
                        "title": contract.title, "clause": clause,
                        "answer": ans.text,
                        "citations": [vars(c) for c in ans.citations],
                        "unsupported": ans.unsupported,
                        "retrieval_failed": ans.retrieval_failed,
                        "seconds": round(time.time() - t0, 1),
                    }
                    out.write(json.dumps(rec) + "\n")
                    out.flush()
                    done[(contract.title, clause)] = rec
                print(f"[{ci + 1}/{len(contracts)}] {contract.title[:55]}",
                      file=sys.stderr)

    _report(args, run_dir, contracts, done)


def _report(args, run_dir, contracts, done):
    by_title = {c.title: c for c in contracts}
    present_hits = present_strict = present_total = 0
    absent_ok = absent_total = 0
    per_clause: dict[str, list[int]] = {}

    for (title, clause), rec in done.items():
        contract = by_title.get(title)
        if contract is None:
            continue
        gold = contract.gold.get(clause, [])
        if gold:
            hit = int(citation_hits_gold(rec["citations"], gold))
            present_hits += hit
            present_strict += int(citation_hits_gold(rec["citations"], gold, strict=True))
            present_total += 1
            per_clause.setdefault(clause, []).append(hit)
        else:
            # absent clause: success = no grounded citation pointing somewhere
            absent_ok += int(len(rec["citations"]) == 0)
            absent_total += 1

    lines = [
        f"# Q&A citation eval: {args.run}",
        f"\nContracts: {len({t for t, _ in done})} ({args.split} split)",
        f"\nCitation hit = a citation covers >= {GOLD_COVERAGE:.0%} of a gold "
        "span (or matches it verbatim). Coverage, not IoU: a Q&A citation is a "
        "passage that should contain the answer, not a minimal span.",
        "\n| Clause | hit rate | n |",
        "|---|---|---|",
    ]
    for clause in sorted(per_clause):
        hits = per_clause[clause]
        lines.append(f"| {clause} | {sum(hits) / len(hits):.2f} | {len(hits)} |")
    hit_rate = present_hits / present_total if present_total else 0.0
    strict_rate = present_strict / present_total if present_total else 0.0
    abs_rate = absent_ok / absent_total if absent_total else 0.0
    lines.append(
        f"\n**Citation hit rate (clause present): {hit_rate:.2f}** "
        f"({present_hits}/{present_total})")
    lines.append(
        f"**Absence handling (clause absent, no citation): {abs_rate:.2f}** "
        f"({absent_ok}/{absent_total})")
    lines.append(
        f"\nStrict IoU >= {IOU_THRESHOLD} hit rate (for reference): "
        f"{strict_rate:.2f} ({present_strict}/{present_total})")
    text = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
