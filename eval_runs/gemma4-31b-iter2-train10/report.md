# Eval report: gemma4-31b-iter2-train10

Contracts evaluated: 10 (train split)
Span match: char IoU >= 0.3

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.62 | 0.45 | 0.53 | 5 | 3 | 6 | 1.00 (1) |
| anti_assignment | 0.80 | 0.44 | 0.57 | 4 | 1 | 5 | 0.80 (5) |
| audit_rights | 0.80 | 1.00 | 0.89 | 4 | 1 | 0 | 1.00 (7) |
| cap_on_liability | 0.36 | 0.56 | 0.43 | 5 | 9 | 4 | 0.57 (7) |
| document_name | 0.25 | 0.30 | 0.27 | 3 | 9 | 7 | — |
| exclusivity | 0.00 | 0.00 | 0.00 | 0 | 2 | 0 | 0.80 (10) |
| expiration_date | 0.57 | 0.80 | 0.67 | 4 | 3 | 1 | 1.00 (5) |
| governing_law | 0.88 | 0.88 | 0.88 | 7 | 1 | 1 | 1.00 (2) |
| license_grant | 1.00 | 0.50 | 0.67 | 4 | 0 | 4 | 1.00 (8) |
| non_compete | 0.00 | 0.00 | 0.00 | 0 | 1 | 0 | 0.90 (10) |
| parties | 0.51 | 0.74 | 0.60 | 39 | 37 | 14 | — |
| renewal_term | 1.00 | 1.00 | 1.00 | 2 | 0 | 0 | 1.00 (8) |
| termination_for_convenience | 0.67 | 0.57 | 0.62 | 4 | 2 | 3 | 1.00 (6) |
| uncapped_liability | 0.00 | 0.00 | 0.00 | 0 | 0 | 1 | 1.00 (9) |
| **micro** | **0.54** | **0.64** | **0.58** | 81 | 69 | 46 | |

Macro F1: 0.509
