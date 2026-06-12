# Eval report: gemma4-31b-baseline-train10

Contracts evaluated: 10 (train split)
Span match: char IoU >= 0.3

| Clause | P | R | F1 | TP | FP | FN | Absent-spec |
|---|---|---|---|---|---|---|---|
| agreement_date | 0.43 | 0.55 | 0.48 | 6 | 8 | 5 | 1.00 (1) |
| anti_assignment | 0.83 | 0.56 | 0.67 | 5 | 1 | 4 | 0.80 (5) |
| audit_rights | 0.57 | 1.00 | 0.73 | 4 | 3 | 0 | 1.00 (7) |
| cap_on_liability | 0.38 | 0.33 | 0.35 | 3 | 5 | 6 | 0.71 (7) |
| document_name | 0.19 | 0.60 | 0.29 | 6 | 25 | 4 | — |
| exclusivity | 0.00 | 0.00 | 0.00 | 0 | 1 | 0 | 0.90 (10) |
| expiration_date | 0.00 | 0.00 | 0.00 | 0 | 1 | 5 | 1.00 (5) |
| governing_law | 0.88 | 0.88 | 0.88 | 7 | 1 | 1 | 1.00 (2) |
| license_grant | 1.00 | 0.50 | 0.67 | 4 | 0 | 4 | 1.00 (8) |
| non_compete | 0.00 | 0.00 | 0.00 | 0 | 1 | 0 | 0.90 (10) |
| parties | 0.16 | 0.30 | 0.21 | 16 | 85 | 37 | — |
| renewal_term | 1.00 | 1.00 | 1.00 | 2 | 0 | 0 | 1.00 (8) |
| termination_for_convenience | 0.50 | 0.43 | 0.46 | 3 | 3 | 4 | 1.00 (6) |
| uncapped_liability | 0.00 | 0.00 | 0.00 | 0 | 0 | 1 | 1.00 (9) |
| **micro** | **0.29** | **0.44** | **0.35** | 56 | 134 | 71 | |

Macro F1: 0.409
