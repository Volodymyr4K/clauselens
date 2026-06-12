# ClauseLens

> ⚠️ **Work in progress** — built in the open. Metrics below will be filled in
> as they are actually measured, not before.

AI-powered contract analysis: extracts key clauses from legal contracts, flags
risky terms, and answers questions about a document with exact citations —
evaluated honestly against expert annotations from the
[CUAD dataset](https://www.atticusprojectai.org/cuad) (510 real contracts
annotated by lawyers).

## What it does

- **Clause extraction** — finds and classifies 14 key clause types
  (governing law, liability caps, termination, non-compete, exclusivity, …)
- **Risk flagging** — highlights potentially problematic terms with explanations
- **Q&A with citations** — ask questions about a contract, get answers grounded
  in exact passages from the document
- **Honest evaluation** — precision / recall / F1 per clause type, measured
  against lawyer-annotated ground truth on a held-out test split

## Design principles

- One system done properly, not a "platform" done halfway
- Provider-agnostic LLM layer: runs on a local model (privacy mode — contracts
  never leave your machine) or any OpenAI-compatible API
- Every number in this README is reproducible by running the eval pipeline

## Status

- [x] Dataset analysis, clause type selection, eval design
- [ ] Extraction pipeline
- [ ] Evaluation pipeline + first measured metrics
- [ ] Q&A with citations
- [ ] Web UI
- [ ] Final report

## Getting started

```bash
./scripts/download_data.sh   # fetch CUAD v1 (~58 MB)
```

More to come as the pipeline lands.

## License

MIT. CUAD dataset © The Atticus Project, CC BY 4.0.
