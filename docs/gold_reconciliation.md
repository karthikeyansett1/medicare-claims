# Gold reconciliation

Verified 2026-10-12T19:42:24.386811+00:00

Checks: 54/54 passed.
Independently compared 11,709,022 member-year fields without fact-to-fact joins.

| Model | Rows |
| --- | ---: |
| dim_member | 232,747 |
| dim_member_year | 687,502 |
| dim_provider | 1,234,675 |
| dim_date | 1,131 |
| fct_professional_lines | 18,787,937 |
| fct_inpatient_stays | 133,139 |
| fct_outpatient_claims | 1,561,368 |
| fct_rx_fills | 11,113,575 |
| fct_member_year_cost | 688,766 |

See [JSON evidence](gold_reconciliation.json) for individual checks, financial scopes,
indexes, outside-enrollment years, and the calendar range. Prescription gross cost
is never labeled Medicare paid. These checks cover the selected samples.
