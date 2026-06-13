"""FastAPI app: upload a contract, see clauses highlighted, ask questions.

Two ways to view a contract's clauses:
- live extraction (`POST /api/extract`) and Q&A (`POST /api/ask`) call the LLM;
- the demo endpoints serve clauses already cached under eval_runs/, so the UI
  is fully explorable with zero API calls (useful when the free quota is spent).
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .clauses import BY_KEY
from .dataset import load_contracts
from .llm import LLMClient
from .qa import answer_question
from .render import Highlight, render_highlighted

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
RUNS_DIR = ROOT / "eval_runs"

app = FastAPI(title="ClauseLens")


@lru_cache(maxsize=1)
def _contracts():
    return load_contracts()


@lru_cache(maxsize=1)
def _demo_cache() -> dict[str, list[dict]]:
    """title -> cached extracted spans, gathered from all eval_runs predictions."""
    cache: dict[str, list[dict]] = {}
    for pred in RUNS_DIR.glob("*/predictions.jsonl"):
        for line in pred.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("spans") and rec["title"] not in cache:
                cache[rec["title"]] = rec["spans"]
    return cache


def _clause_view(spans: list[dict]) -> list[dict]:
    return [
        {
            "clause": s["clause"],
            "label": BY_KEY[s["clause"]].cuad_name if s["clause"] in BY_KEY else s["clause"],
            "risk": BY_KEY[s["clause"]].risk if s["clause"] in BY_KEY else False,
            "text": s["text"],
            "start": s["start"],
            "end": s["end"],
        }
        for s in sorted(spans, key=lambda s: s["start"])
    ]


def _payload(title: str, text: str, spans: list[dict]) -> dict:
    highlights = [Highlight(s["start"], s["end"], s["clause"]) for s in spans]
    return {
        "title": title,
        "highlighted_html": render_highlighted(text, highlights),
        "clauses": _clause_view(spans),
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/contracts")
def list_contracts():
    """Contracts that have cached extraction, so the demo works offline."""
    cache = _demo_cache()
    out = []
    for i, c in enumerate(_contracts()):
        if c.title in cache:
            out.append({"idx": i, "title": c.title, "chars": len(c.text)})
    return sorted(out, key=lambda x: x["title"])[:200]


@app.get("/api/demo/{idx}")
def demo(idx: int):
    contracts = _contracts()
    if not 0 <= idx < len(contracts):
        raise HTTPException(404, "no such contract")
    c = contracts[idx]
    spans = _demo_cache().get(c.title)
    if spans is None:
        raise HTTPException(404, "no cached extraction for this contract")
    return _payload(c.title, c.text, spans)


class AskRequest(BaseModel):
    idx: int
    question: str


@app.post("/api/ask")
def ask(req: AskRequest):
    contracts = _contracts()
    if not 0 <= req.idx < len(contracts):
        raise HTTPException(404, "no such contract")
    c = contracts[req.idx]
    ans = answer_question(c.text, req.question, LLMClient())
    if ans.retrieval_failed:
        raise HTTPException(503, "LLM endpoint unavailable")
    return {
        "answer": ans.text,
        "unsupported": ans.unsupported,
        "citations": [{"text": x.text, "start": x.start, "end": x.end}
                      for x in ans.citations],
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")
