"""Run clause-extraction eval on a CUAD split subset. Resumable.

Predictions are cached per contract in eval_runs/<run>/predictions.jsonl, so
an interrupted run (rate limits, flaky endpoints) picks up where it left off
and metrics can be recomputed without re-running the model.

Usage:
    uv run python scripts/run_eval.py --run nemotron-train10 --split train -n 10
    uv run python scripts/run_eval.py --run nemotron-train10 --report-only
"""

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

from clauselens.dataset import DATA_DIR, load_contracts
from clauselens.evaluation import IOU_THRESHOLD, aggregate, match_contract
from clauselens.extraction import ExtractedSpan, extract_clauses
from clauselens.llm import LLMClient

RUNS_DIR = Path(__file__).resolve().parents[1] / "eval_runs"


def select_contracts(split: str, n: int):
    """Deterministic, length-stratified subset: sort by length, even strides."""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run name, e.g. nemotron-train10")
    ap.add_argument("--split", choices=["train", "test"], default="train")
    ap.add_argument("-n", type=int, default=10, help="number of contracts")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    run_dir = RUNS_DIR / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    pred_file = run_dir / "predictions.jsonl"

    done: dict[str, list[ExtractedSpan]] = {}
    if pred_file.exists():
        for line in pred_file.read_text().splitlines():
            rec = json.loads(line)
            done[rec["title"]] = [ExtractedSpan(**s) for s in rec["spans"]]

    contracts = select_contracts(args.split, args.n)

    if not args.report_only:
        client = LLMClient()
        meta = {
            "model": client.model, "base_url": client.base_url,
            "split": args.split, "n": args.n, "iou_threshold": IOU_THRESHOLD,
        }
        meta_file = run_dir / "meta.json"
        if meta_file.exists():
            prev = json.loads(meta_file.read_text())
            same_setup = all(prev.get(k) == meta[k] for k in ("model", "split"))
            if not same_setup:
                sys.exit(
                    f"refusing to resume '{args.run}': it was started with "
                    f"{prev.get('model')} on {prev.get('split')} split, current "
                    f"config is {meta['model']} on {meta['split']}. Mixing models "
                    "in one run would corrupt the metrics — use a new --run name.")
        meta_file.write_text(json.dumps(meta, indent=2))
        with pred_file.open("a") as out:
            for i, contract in enumerate(contracts):
                if contract.title in done:
                    continue
                t0 = time.time()
                result = extract_clauses(contract.text, client)
                rec = {
                    "title": contract.title,
                    "spans": [dataclasses.asdict(s) for s in result.spans],
                    "dropped_ungrounded": result.dropped_ungrounded,
                    "failed_chunks": result.failed_chunks,
                    "total_chunks": result.total_chunks,
                    "seconds": round(time.time() - t0, 1),
                }
                out.write(json.dumps(rec) + "\n")
                out.flush()
                done[contract.title] = result.spans
                warn = (f" [LOST {result.failed_chunks}/{result.total_chunks} chunks]"
                        if result.failed_chunks else "")
                print(f"[{i + 1}/{len(contracts)}] {contract.title}"
                      f" ({len(contract.text)} chars, {rec['seconds']}s,"
                      f" {len(result.spans)} spans){warn}", file=sys.stderr)

    if args.report_only:
        # score every cached contract, not a -n-sized subset of them
        by_title = {c.title: c for c in load_contracts()}
        if args.split == "test":
            by_title = {c.title: c for c in load_contracts(DATA_DIR / "test.json")}
        evaluated = [by_title[t] for t in done if t in by_title]
    else:
        evaluated = [c for c in contracts if c.title in done]
    if not evaluated:
        print("no predictions yet", file=sys.stderr)
        return
    report = aggregate(
        [match_contract(done[c.title], c, text_match=True) for c in evaluated])
    strict = aggregate(
        [match_contract(done[c.title], c, text_match=False) for c in evaluated])

    lines = [
        f"# Eval report: {args.run}",
        f"\nContracts evaluated: {len(evaluated)} ({args.split} split)",
        f"Match: char IoU >= {IOU_THRESHOLD} OR verbatim text match",
        "\n| Clause | P | R | F1 | TP | FP | FN | Absent-spec |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for clause in sorted(report.per_clause):
        c = report.per_clause[clause]
        a = report.absence.get(clause)
        spec = f"{a.specificity:.2f} ({a.true_absent + a.false_found})" if a else "—"
        lines.append(
            f"| {clause} | {c.precision:.2f} | {c.recall:.2f} | {c.f1:.2f} "
            f"| {c.tp} | {c.fp} | {c.fn} | {spec} |")
    m = report.micro()
    lines.append(
        f"| **micro** | **{m.precision:.2f}** | **{m.recall:.2f}** "
        f"| **{m.f1:.2f}** | {m.tp} | {m.fp} | {m.fn} | |")
    sm = strict.micro()
    lines.append(f"\nMacro F1: {report.macro_f1():.3f}")
    lines.append(
        f"\nStrict positional-only (IoU match, no text-match arm): "
        f"micro F1 {sm.f1:.3f}, macro F1 {strict.macro_f1():.3f}")
    reportText = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(reportText)
    print(reportText)


if __name__ == "__main__":
    main()
