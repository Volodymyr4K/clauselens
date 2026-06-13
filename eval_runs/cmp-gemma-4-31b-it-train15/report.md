# Eval report: cmp-gemma-4-31b-it-train15

Contracts evaluated: 15 (train split)
Match: char IoU >= 0.3 OR verbatim text match

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.73 | 0.65 | 0.69 | 11 | 4 | 6 | — |
| anti_assignment | 0.86 | 0.33 | 0.48 | 6 | 1 | 12 | 1.00 (6) |
| audit_rights | 0.88 | 0.50 | 0.64 | 7 | 1 | 7 | 1.00 (10) |
| cap_on_liability | 0.65 | 0.69 | 0.67 | 11 | 6 | 5 | 0.78 (9) |
| document_name | 0.70 | 0.93 | 0.80 | 14 | 6 | 1 | — |
| exclusivity | 0.23 | 0.38 | 0.29 | 3 | 10 | 5 | 0.69 (13) |
| expiration_date | 0.26 | 0.69 | 0.38 | 9 | 25 | 4 | 1.00 (3) |
| governing_law | 0.92 | 0.79 | 0.85 | 11 | 1 | 3 | 1.00 (2) |
| license_grant | 0.83 | 0.56 | 0.67 | 15 | 3 | 12 | 0.89 (9) |
| non_compete | 0.00 | 0.00 | 0.00 | 0 | 2 | 3 | 0.86 (14) |
| parties | 0.53 | 0.77 | 0.63 | 49 | 43 | 15 | — |
| renewal_term | 1.00 | 0.75 | 0.86 | 3 | 0 | 1 | 1.00 (11) |
| termination_for_convenience | 0.38 | 0.50 | 0.43 | 3 | 5 | 3 | 0.73 (11) |
| uncapped_liability | 0.67 | 0.67 | 0.67 | 2 | 1 | 1 | 0.92 (13) |
| **micro** | **0.57** | **0.65** | **0.61** | 144 | 108 | 78 | |

Macro F1: 0.574

Strict positional-only (IoU match, no text-match arm): micro F1 0.553, macro F1 0.533
