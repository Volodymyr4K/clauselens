"""Ask a free-form question about a CUAD contract.

Usage:
    uv run python scripts/ask.py [contract_index] "your question"
"""

import sys

from clauselens.dataset import load_contracts
from clauselens.llm import LLMClient
from clauselens.qa import answer_question


def main() -> None:
    idx = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    question = sys.argv[-1]
    contract = load_contracts()[idx]
    print(f"Contract: {contract.title}\nQuestion: {question}\n")

    ans = answer_question(contract.text, question, LLMClient())
    if ans.retrieval_failed:
        print("(endpoint failed)")
        return
    print(f"Answer: {ans.text}\n")
    if ans.unsupported:
        print("⚠ unsupported: model gave no quote that exists in the contract")
    for c in ans.citations:
        print(f"  cite @{c.start}: {c.text[:160]!r}")


if __name__ == "__main__":
    main()
