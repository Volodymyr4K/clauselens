"""Loading CUAD contracts and gold annotations."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .clauses import BY_CUAD_NAME

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_CATEGORY_RE = re.compile(r'related to "(.+?)"')


@dataclass
class GoldSpan:
    text: str
    start: int  # char offset in the contract text


@dataclass
class Contract:
    title: str
    text: str
    # clause key -> gold spans (empty list = annotators found none)
    gold: dict[str, list[GoldSpan]] = field(default_factory=dict)


def load_contracts(path: Path | str = DATA_DIR / "CUADv1.json") -> list[Contract]:
    raw = json.loads(Path(path).read_text())["data"]
    contracts = []
    for item in raw:
        para = item["paragraphs"][0]
        contract = Contract(title=item["title"], text=para["context"])
        for qa in para["qas"]:
            m = _CATEGORY_RE.search(qa["question"])
            if not m or m.group(1) not in BY_CUAD_NAME:
                continue
            key = BY_CUAD_NAME[m.group(1)].key
            contract.gold[key] = [
                GoldSpan(a["text"], a["answer_start"]) for a in qa["answers"]
            ]
        contracts.append(contract)
    return contracts
