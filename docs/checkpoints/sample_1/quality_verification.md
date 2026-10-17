# Step 6 verification

Verified 2026-10-09T16:38:09.451000+00:00 against local Sample 1.

Full dbt build: **21 models and 1 seed succeeded; 76 data tests passed, 3 warned; 6 unit tests passed.** No errors or skipped nodes. Elapsed: 584.5 seconds.

The 79 data tests and 6 unit tests are counted separately from models and seeds. This includes 21 added data tests beyond Step 5. The 30-day boundary fixture is one of the data tests, not a native dbt unit test.

| Warning monitor | Flagged records |
|---|---:|
| `monitor_facility_header_conflicts` | 11,043 |
| `monitor_missing_service_dates` | 278 |
| `monitor_negative_medical_payments` | 2,621 |

Warnings preserve and expose source anomalies; counts can overlap across monitors. Negative-payment flags identify events containing a negative source amount, including a negative facility segment even if the net claim payment is positive. Header conflicts count claim episodes, not segments. Missing service dates use each fact’s cost-assignment date.

The post-death monitor passed with no events starting more than 30 days after the earliest observed member death date. Null dates are covered by the separate warning monitor.

- SQLFluff 3.5.0: all 21 models, zero violations under the configured rules.
- Python regression suite: 34 passed, including isolated PostgreSQL loader tests.
- Independent post-build reconciliation: 146 silver checks and 53 gold checks passed.
- Build-manifest comparison: 20 models match exactly; silver_pde_fills differs only in SELECT whitespace formatting. Input hashes are recorded in the JSON evidence.

Run reconciliation only after dbt writes finish. CCS and attribution tests are deferred until those models exist. No real-world provider conclusions follow from this synthetic dataset.

See [checkpoint notes](steps/06-quality.md) for the rationale and interview explanation, and [full evidence](quality_verification.json) for every test result.
