# Step 11b: Sample 2 integration

The original guide requires Samples 1 and 2. Earlier checkpoints intentionally
established the end-to-end pipeline on Sample 1. This checkpoint adds Sample 2
before assistant evaluation, with independent source evidence and a combined
warehouse rebuilt from the original CSVs.

## What changed and why

The eight Sample 2 CMS archives use the source URLs in `ingest/urls.yaml`.
Cached downloads can be adopted with `--cache-manifest`: configured URL and
filename, SHA-256, size, safe member identity and full ZIP CRC are verified before
normal extraction. The original source URL is recorded; an unrecorded redirect
URL is left blank rather than inferred. Source data remain ignored by Git.

`ingest.samples` defines CMS Table 2 counts and shared sample selection.
`MEDICARE_SAMPLES=1,2` is the Makefile and warehouse verifier default; use
`MEDICARE_SAMPLES=1` for a deliberate single-sample rebuild. Acquisition and
profiling accept `--sample`; bronze and silver/gold verifiers accept `--samples`.
Sample 1 retains `docs/data_profile.json`; Sample 2 uses
`docs/data_profile_sample_2.json`. Each profile uses its own temporary SQLite
keys and beneficiary context, so identical raw identifiers across samples cannot
contaminate source diagnostics.

The bronze loader constructs all sixteen source plans, verifies headers across
samples, and calls the loader once. One transaction truncates and reloads all
five tables and commits only after exact file-level count, lineage, hash and
financial reconciliation. Calling the old single-sample load twice would have
replaced Sample 1; the combined plan prevents this failure. Tests cover identical
raw IDs across samples, schema mismatch before database access, both-sample
retention, and rollback when the second sample fails reconciliation.

Current reconciliation outputs describe the combined warehouse. The prior
Sample 1 reports and comparison outputs are retained under
`docs/checkpoints/sample_1/`. Earlier step notes retain their historical scope.

## Reproduce

```sh
make download verify-data profile
make bronze
make pipeline-build
make verify-bronze verify-silver verify-gold verify-attribution verify-grouper
make verify-readmissions verify-metrics compare verify-comparison
make test-db
```

`pipeline-build` runs core dbt models first, then retrains expected costs from
2008, then builds the dependent provider mart. Independent verifiers run after
all model writes finish. Comparisons remain partitioned by sample and year;
they do not treat the two samples as one provider-ranking population.

## Interview explanation

“I expanded the warehouse to a second independent synthetic sample without
changing the raw data or losing the first sample. I separated source profiling
contexts, validated compatible schemas before loading, and made both samples
one atomic load. I then rebuilt the downstream models and independently
reconciled counts and money. Provider comparisons keep sample and year in their
grain, so a matching raw identifier cannot silently join unrelated records.”

## Source evidence

| File | Sample 1 | Sample 2 | Combined |
| --- | ---: | ---: | ---: |
| beneficiary_2008 | 116,352 | 116,395 | 232,747 |
| beneficiary_2009 | 114,538 | 114,618 | 229,156 |
| beneficiary_2010 | 112,754 | 112,845 | 225,599 |
| inpatient | 66,773 | 66,494 | 133,267 |
| outpatient | 790,790 | 792,562 | 1,583,352 |
| carrier_a | 2,370,667 | 2,372,957 | 4,743,624 |
| carrier_b | 2,370,668 | 2,372,957 | 4,743,625 |
| pde | 5,552,421 | 5,561,154 | 11,113,575 |
| **Total** | **11,494,963** | **11,509,982** | **23,004,945** |

All sixteen file counts match CMS Table 2. Sample 2 has zero orphan member
rows in all eight files, zero inconsistent death dates, and zero later-year
beneficiaries outside its 2008 sample. Source profiling completed in 162.58s.
Sample 2 carrier slots without HCPCS account for $20,639,950 of paid amounts;
these slots remain in professional spending. They are not office-visit evidence.
Combined bronze committed all 23,004,945 rows with exact file-level financial
reconciliation in 114.86s. These are measured local runtimes, not performance
benchmarks or guarantees.

## Combined build and independent validation

The full core command used `--no-partial-parse`: 154 passed, three expected
warnings, zero errors and zero skipped nodes (157 total; 1,036.67s). It built
32 table models and two seeds and ran 107 data tests and 16 unit tests. The
warnings retain and flag 22,112 facility header conflicts, 470 missing service
dates and 5,236 negative medical payments; none is silently dropped.
The refit expected-cost model supplies 272,105 performance-year records. The
subsequent metrics build passed all ten nodes (one model, eight data tests and
one unit test) in 4.10s.

Independent bronze verification passed all sixteen source plans. Silver passed
151/151 checks, including per-sample source coverage and exact monetary totals.
Gold passed 54/54 checks and 11,709,022 member-year field comparisons. The first
gold audit exposed one remaining Sample 1-only expected missing-HCPCS payment
constant. Replacing it with selected-profile Decimal sums and adding a regression
resolved the audit without changing warehouse data or rebuilding models.

The combined warehouse contains 232,747 members, 687,502 enrolled member-years,
133,139 inpatient stays, 1,561,368 outpatient claims, 18,787,937 professional
lines and 11,113,575 prescription events. It preserves 25,478,615 diagnosis
positions. Adding Sample 2 also refits the pooled 2008 risk model, so Sample 1
adjusted results can change even though its raw source files are unchanged.


Attribution independently checked 8,068,321 fact lines and reconstructed all
544,210 assignments with zero mismatches. CCS verified 15,072 reference codes,
820 category/year groups and $1,273,323,410.00 inpatient paid; 99.9471% of
source diagnosis positions mapped. Readmission reconstruction checked 1,674,582
fields across 128,814 merged episodes, with 3,233 readmissions among 49,998
eligible indices (6.4663%). Metrics checked 323,458 provider panels, including
872 qualifying panels, and 4,531,900 numeric/rank comparisons.

Comparison verification passed 60 comparisons and 6,991 provider pairs across
all four sample/year cohorts, including 28,684 independent SQL numeric checks
and 3,104 mart rank/decile checks. All three refreshed charts were visually
inspected: four readable panels in each rank/movement chart and the combined
128,814-to-49,998 episode waterfall. `make compare` now regenerates the report
through the checked-in `analysis/render_findings.py`.

Full Python/PostgreSQL regression suite: **63 passed, zero failures, zero skipped**.
No dbt SQL changed in this integration. Exact evidence is in
[sample2_integration_verification.json](../sample2_integration_verification.json).

## Current findings

Sample 2 reassignment among jointly attributed members is 87.8% in 2009 and
86.1% in 2010. Its A/B PMPM Spearman correlations are 0.353 and 0.055, with
43/117 and 44/84 common qualifying providers moving at least three deciles.
The four-cohort report retains Sample 1 results separately rather than averaging
incompatible ranking populations.

The current largest global mover is synthetic NPI `2639271506`, Sample 2,
2009: decile 10 to 1, rank 119/130 to 12/129, and PMPM $730.95 to $329.42.
Only two members remain; 19 leave and 24 enter. Outgoing medical paid exceeds
incoming paid by $81,420, including $49,890 outpatient and $23,530 professional
spending. This explains cohort composition, not clinical causation or services
rendered by that attributed provider. The refreshed risk model's expected/observed
paid ratios are 1.103 and 1.160 in 2009/2010; adjustment is descriptive and
not clinically validated. See [full findings](../../analysis/findings.md).

## Publication

Published in [draft PR #12](https://github.com/karthikeyansett1/medicare-claims/pull/12)
from `codex/step-11b-sample2`, based on `codex/step-11-comparison`,
under the standing authorization to commit and push verified checkpoints.
Earlier draft PRs remain unmerged. The next checkpoint implements the assistant
against the verified combined Sample 1 and Sample 2 dataset.
