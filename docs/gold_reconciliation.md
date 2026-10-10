# Gold reconciliation

Verified 2026-10-09T16:37:37.815203+00:00

Checks: 53/53 passed.
Independently compared 5,853,015 member-year fields without fact-to-fact joins.

| Model | Rows |
| --- | ---: |
| dim_member | 116,352 |
| dim_member_year | 343,644 |
| dim_provider | 617,199 |
| dim_date | 1,131 |
| fct_professional_lines | 9,388,987 |
| fct_inpatient_stays | 66,705 |
| fct_outpatient_claims | 779,815 |
| fct_rx_fills | 5,552,421 |
| fct_member_year_cost | 344,295 |

See [JSON evidence](gold_reconciliation.json) for individual checks, financial scopes,
indexes, outside-enrollment years, and the calendar range. Prescription gross cost
is never labeled Medicare paid. These are local Sample 1 checks.
