# Q&A citation eval: qa-gemma4-31b-train10

Contracts: 10 (train split)

Citation hit = a citation covers >= 50% of a gold span (or matches it verbatim). Coverage, not IoU: a Q&A citation is a passage that should contain the answer, not a minimal span.

| Clause | hit rate | n |
|---|---|---|
| agreement_date | 0.67 | 9 |
| anti_assignment | 0.40 | 5 |
| audit_rights | 0.00 | 3 |
| cap_on_liability | 0.33 | 3 |
| document_name | 0.40 | 10 |
| expiration_date | 0.80 | 5 |
| governing_law | 0.62 | 8 |
| license_grant | 0.50 | 2 |
| parties | 0.30 | 10 |
| renewal_term | 1.00 | 2 |
| termination_for_convenience | 1.00 | 4 |
| uncapped_liability | 0.00 | 1 |

**Citation hit rate (clause present): 0.52** (32/62)
**Absence handling (clause absent, no citation): 0.83** (65/78)

Strict IoU >= 0.3 hit rate (for reference): 0.42 (26/62)
