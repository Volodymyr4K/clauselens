# Eval report: gemma4-31b-iter2-train30

Contracts evaluated: 30 (train split)
Match: char IoU >= 0.3 OR verbatim text match

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.76 | 0.73 | 0.75 | 22 | 7 | 8 | 1.00 (2) |
| anti_assignment | 0.80 | 0.52 | 0.63 | 16 | 4 | 15 | 0.92 (12) |
| audit_rights | 0.73 | 0.68 | 0.70 | 19 | 7 | 9 | 0.94 (18) |
| cap_on_liability | 0.61 | 0.65 | 0.63 | 31 | 20 | 17 | 0.67 (15) |
| document_name | 0.71 | 0.90 | 0.79 | 27 | 11 | 3 | — |
| exclusivity | 0.36 | 0.62 | 0.46 | 8 | 14 | 5 | 0.68 (25) |
| expiration_date | 0.38 | 0.71 | 0.49 | 17 | 28 | 7 | 1.00 (7) |
| governing_law | 0.96 | 0.89 | 0.92 | 24 | 1 | 3 | 1.00 (4) |
| license_grant | 0.88 | 0.59 | 0.71 | 22 | 3 | 15 | 0.95 (19) |
| non_compete | 0.50 | 0.33 | 0.40 | 2 | 2 | 4 | 0.93 (27) |
| parties | 0.56 | 0.80 | 0.66 | 110 | 87 | 28 | — |
| renewal_term | 0.78 | 0.70 | 0.74 | 7 | 2 | 3 | 0.95 (21) |
| termination_for_convenience | 0.60 | 0.67 | 0.63 | 12 | 8 | 6 | 0.88 (17) |
| uncapped_liability | 0.67 | 0.40 | 0.50 | 4 | 2 | 6 | 0.92 (24) |
| **micro** | **0.62** | **0.71** | **0.66** | 321 | 196 | 129 | |

Macro F1: 0.643

Strict positional-only (IoU match, no text-match arm): micro F1 0.614, macro F1 0.604
