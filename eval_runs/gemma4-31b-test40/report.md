# Eval report: gemma4-31b-test40

Contracts evaluated: 20 (test split)
Match: char IoU >= 0.3 OR verbatim text match

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.80 | 0.94 | 0.86 | 16 | 4 | 1 | 0.67 (3) |
| anti_assignment | 0.93 | 0.82 | 0.87 | 14 | 1 | 3 | 1.00 (9) |
| audit_rights | 0.67 | 1.00 | 0.80 | 6 | 3 | 0 | 0.81 (16) |
| cap_on_liability | 0.71 | 0.83 | 0.77 | 15 | 6 | 3 | 0.85 (13) |
| document_name | 0.69 | 0.90 | 0.78 | 18 | 8 | 2 | — |
| exclusivity | 0.67 | 1.00 | 0.80 | 4 | 2 | 0 | 0.95 (19) |
| expiration_date | 0.69 | 0.82 | 0.75 | 9 | 4 | 2 | 0.78 (9) |
| governing_law | 1.00 | 1.00 | 1.00 | 14 | 0 | 0 | 1.00 (6) |
| license_grant | 0.80 | 0.89 | 0.84 | 8 | 2 | 1 | 0.87 (15) |
| non_compete | 0.00 | 0.00 | 0.00 | 0 | 2 | 1 | 0.89 (19) |
| parties | 0.60 | 0.80 | 0.69 | 80 | 53 | 20 | — |
| renewal_term | 0.71 | 1.00 | 0.83 | 5 | 2 | 0 | 1.00 (15) |
| termination_for_convenience | 0.67 | 1.00 | 0.80 | 6 | 3 | 0 | 0.79 (14) |
| uncapped_liability | 1.00 | 1.00 | 1.00 | 2 | 0 | 0 | 1.00 (18) |
| **micro** | **0.69** | **0.86** | **0.76** | 197 | 90 | 33 | |

Macro F1: 0.772

Strict positional-only (IoU match, no text-match arm): micro F1 0.716, macro F1 0.747
