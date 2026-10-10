# Silver reconciliation

Verified: 2026-10-09T16:37:10.229116+00:00

Checks: 146/146 passed; exact decimal comparisons.

| Model | Rows |
| --- | ---: |
| stg_beneficiary | 343,644 |
| stg_inpatient | 66,773 |
| stg_outpatient | 790,790 |
| stg_carrier | 4,741,335 |
| stg_pde | 5,552,421 |
| silver_carrier_lines | 9,388,987 |
| silver_diagnoses | 12,733,072 |
| silver_inpatient_stays | 66,705 |
| silver_outpatient_claims | 779,815 |
| silver_member_months | 343,644 |
| silver_pde_fills | 5,552,421 |
| silver_cast_audit | 8 |

Full individual comparisons, cast-error counts, conflict flags, and enrollment
counts are in [the JSON evidence](silver_reconciliation.json).
Financial scopes remain separate: medical Medicare paid, carrier allowed,
drug gross cost, and drug patient payment. No amounts are rounded by safe casts.

This read-only check does not refresh tables. Run `make silver` first after code
changes; the dbt build must pass before treating the checkpoint as complete.
