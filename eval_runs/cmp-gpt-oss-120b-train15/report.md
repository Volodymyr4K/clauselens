# Eval report: cmp-gpt-oss-120b-train15

Contracts evaluated: 15 (train split)
Match: char IoU >= 0.3 OR verbatim text match

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.60 | 0.53 | 0.56 | 9 | 6 | 8 | — |
| anti_assignment | 0.60 | 0.33 | 0.43 | 6 | 4 | 12 | 1.00 (6) |
| audit_rights | 0.73 | 0.57 | 0.64 | 8 | 3 | 6 | 1.00 (10) |
| cap_on_liability | 0.82 | 0.56 | 0.67 | 9 | 2 | 7 | 1.00 (9) |
| document_name | 0.72 | 0.87 | 0.79 | 13 | 5 | 2 | — |
| exclusivity | 0.50 | 0.25 | 0.33 | 2 | 2 | 6 | 1.00 (13) |
| expiration_date | 0.28 | 0.69 | 0.40 | 9 | 23 | 4 | 1.00 (3) |
| governing_law | 0.92 | 0.79 | 0.85 | 11 | 1 | 3 | 1.00 (2) |
| license_grant | 0.62 | 0.37 | 0.47 | 10 | 6 | 17 | 1.00 (9) |
| non_compete | 0.00 | 0.00 | 0.00 | 0 | 1 | 3 | 0.93 (14) |
| parties | 0.58 | 0.75 | 0.65 | 48 | 35 | 16 | — |
| renewal_term | 1.00 | 0.75 | 0.86 | 3 | 0 | 1 | 1.00 (11) |
| termination_for_convenience | 0.50 | 0.67 | 0.57 | 4 | 4 | 2 | 0.73 (11) |
| uncapped_liability | 0.00 | 0.00 | 0.00 | 0 | 0 | 3 | 1.00 (13) |
| **micro** | **0.59** | **0.59** | **0.59** | 132 | 92 | 90 | |

Macro F1: 0.515

Strict positional-only (IoU match, no text-match arm): micro F1 0.538, macro F1 0.476
