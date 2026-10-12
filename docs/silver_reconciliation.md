# Silver reconciliation

Verified: 2026-10-11T16:05:08.238011+00:00

Checks: 151/151 passed; exact decimal comparisons.

| Model | Rows |
| --- | ---: |
| stg_beneficiary | 687,502 |
| stg_inpatient | 133,267 |
| stg_outpatient | 1,583,352 |
| stg_carrier | 9,487,249 |
| stg_pde | 11,113,575 |
| silver_carrier_lines | 18,787,937 |
| silver_diagnoses | 25,478,615 |
| silver_inpatient_stays | 133,139 |
| silver_outpatient_claims | 1,561,368 |
| silver_member_months | 687,502 |
| silver_pde_fills | 11,113,575 |
| silver_cast_audit | 16 |

Full individual comparisons, cast-error counts, conflict flags, and enrollment
counts are in [the JSON evidence](silver_reconciliation.json).
Financial scopes remain separate: medical Medicare paid, carrier allowed,
drug gross cost, and drug patient payment. No amounts are rounded by safe casts.

This read-only check does not refresh tables. Run `make silver` first after code
changes; the dbt build must pass before treating the checkpoint as complete.
