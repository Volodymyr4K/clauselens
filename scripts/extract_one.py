"""Run clause extraction on a single CUAD contract and compare with gold labels.

Usage:
    uv run python scripts/extract_one.py [contract_index]
"""

import sys
import time

from clauselens.dataset import load_contracts
from clauselens.extraction import extract_clauses
from clauselens.llm import LLMClient


def main() -> None:
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    contract = load_contracts()[idx]
    print(f"Contract: {contract.title}")
    print(f"Length: {len(contract.text)} chars")

    client = LLMClient()
    print(f"Model: {client.model} @ {client.base_url}\n")

    t0 = time.time()
    result = extract_clauses(contract.text, client)
    elapsed = time.time() - t0

    by_clause: dict[str, list] = {}
    for span in result.spans:
        by_clause.setdefault(span.clause, []).append(span)

    for clause, gold_spans in sorted(contract.gold.items()):
        predicted = by_clause.get(clause, [])
        print(f"== {clause} (gold: {len(gold_spans)}, predicted: {len(predicted)})")
        for g in gold_spans:
            print(f"   GOLD @{g.start}: {g.text[:120]!r}")
        for p in predicted:
            print(f"   PRED @{p.start}: {p.text[:120]!r}")

    print(f"\nDropped ungrounded quotes: {result.dropped_ungrounded}")
    print(f"Failed chunks: {result.failed_chunks}/{result.total_chunks}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
