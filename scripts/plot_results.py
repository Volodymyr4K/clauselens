"""Render result charts from cached eval predictions (no LLM calls).

Recomputes metrics from eval_runs/<run>/predictions.jsonl via the same
evaluation module the reports use, then writes PNGs to docs/img/. Charts are
derived from committed predictions, so they are reproducible and cannot drift
from the numbers in the reports.

    uv run --extra viz python scripts/plot_results.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from clauselens.dataset import DATA_DIR, load_contracts  # noqa: E402
from clauselens.evaluation import aggregate, match_contract  # noqa: E402
from clauselens.extraction import ExtractedSpan  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
INK, GRID = "#1e222b", "#d6dae2"
BLUE, ORANGE = "#3b6fd4", "#e07b39"


def load_run(run: str) -> dict[str, list[ExtractedSpan]]:
    path = ROOT / "eval_runs" / run / "predictions.jsonl"
    done = {}
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        done[rec["title"]] = [ExtractedSpan(**s) for s in rec["spans"]]
    return done


def report_for(run: str, split: str):
    done = load_run(run)
    if split == "test":
        by_title = {c.title: c for c in load_contracts(DATA_DIR / "test.json")}
    else:
        test_titles = {c.title for c in load_contracts(DATA_DIR / "test.json")}
        by_title = {c.title: c for c in load_contracts() if c.title not in test_titles}
    contracts = [by_title[t] for t in done if t in by_title]
    return aggregate([match_contract(done[c.title], c) for c in contracts]), len(contracts)


def plot_per_clause(run: str, split: str, out: Path) -> None:
    report, n = report_for(run, split)
    items = sorted(report.per_clause.items(), key=lambda kv: kv[1].f1)
    labels = [k for k, _ in items]
    f1s = [c.f1 for _, c in items]
    micro = report.micro().f1

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = [ORANGE if f < 0.5 else BLUE for f in f1s]
    ax.barh(labels, f1s, color=colors)
    ax.axvline(micro, color=INK, ls="--", lw=1.2, label=f"micro F1 = {micro:.2f}")
    for i, f in enumerate(f1s):
        ax.text(f + 0.01, i, f"{f:.2f}", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("F1 vs lawyer-annotated gold spans")
    ax.set_title(f"Clause extraction F1 by type — Gemma 4 31B, {n} contracts ({split})")
    ax.legend(loc="lower right")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def plot_model_comparison(runs: dict[str, str], split: str, out: Path) -> None:
    names = list(runs)
    micro = []
    macro = []
    for run in runs.values():
        report, _ = report_for(run, split)
        micro.append(report.micro().f1)
        macro.append(report.macro_f1())

    x = range(len(names))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    w = 0.36
    ax.bar([i - w / 2 for i in x], micro, w, label="micro F1", color=BLUE)
    ax.bar([i + w / 2 for i in x], macro, w, label="macro F1", color=ORANGE)
    for i, (mi, ma) in enumerate(zip(micro, macro)):
        ax.text(i - w / 2, mi + 0.01, f"{mi:.2f}", ha="center", fontsize=8)
        ax.text(i + w / 2, ma + 0.01, f"{ma:.2f}", ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("F1")
    ax.set_title("Model comparison — same 15 train contracts")
    ax.legend()
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plot_per_clause("gemma4-31b-iter2-train30", "train", OUT / "extraction_f1_by_clause.png")
    plot_model_comparison(
        {"Gemma 4 31B": "cmp-gemma-4-31b-it-train15",
         "GPT-OSS 120B": "cmp-gpt-oss-120b-train15"},
        "train", OUT / "model_comparison.png")


if __name__ == "__main__":
    main()
