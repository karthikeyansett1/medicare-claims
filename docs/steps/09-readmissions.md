# Step 9 — 30-day all-cause readmissions

## What we are doing

Write the [measure specification](../../assistant/measure_definitions.md) first,
then merge inpatient claim intervals and retain an auditable exclusion reason
for every merged episode. Calculate next admissions before denominator filtering.
Attach eligible indices to both retrospective attribution methods, retaining
unattributed coverage and exposing the existing 20-member reporting threshold.

## Why

Counting claim IDs as hospitalizations can misclassify overlap or transfers as
readmissions. A running maximum discharge handles nested intervals that a simple
LAG misses. Full observation matters: unavailable late-2010 follow-up, uncertain
headers, deaths, and annual enrollment proxies must be explicit denominator rules.
Every source claim and its money is still reconciled, even when clinically excluded.

## Verification

- `make readmissions`: four models, six data tests and four SQL unit tests.
- `make verify-readmissions`: independent Python interval reconstruction,
  eligibility and next-admission computation; 839,280 fields across 64,560 episodes
  and all 161,870 provider rows agree. All 66,705 source inpatient claims occur once.
- SQLFluff passes for all four new models. Existing Python regression suite:
  33 passed, 6 database-only tests skipped in the offline invocation.
- Final targeted build evidence: [14 successful nodes](../readmission_build_verification.json),
  with no warnings, errors, or skips.
- Unit fixtures cover nested overlap, same-day transfers, 1/30/31 days, missing
  dates, conflicting headers/current or next, death on discharge and in follow-up,
  chained indices, December 1/2 cutoff, and cross-year enrollment.
- Overall numerator 1,579 / denominator 25,062 = 6.3004%.
- [Exclusion waterfall and coverage](../readmission_verification.md).
- [Three agent-verified timelines](../../analysis/readmission_spot_check.md).
  These are explicitly not human or clinical validation.

## How to explain it if asked

“I defined a reproducible readmission denominator before coding. I merged
transfers and overlaps with a running maximum, kept an exclusion waterfall,
and independently reconstructed every episode in Python. The observed synthetic
rate was 6.30%. Annual enrollment counts only support a proxy for follow-up,
so I documented conservative exclusions instead of claiming continuous coverage.”

## Limits and next step

This is unadjusted, synthetic, and not a validated CMS measure. There is no
planned-readmission exclusion or discharge-status adjudication. Current or next
header conflicts and any undated member episode trigger conservative exclusion.
Provider panels are retrospective and rates count episodes, not unique people.
Step 10 will add financial/utilization metrics and risk-adjustment methodology.

## Publication

Published from `codex/step-09-readmissions`, based on `codex/step-08-grouper`,
under the user’s standing authorization to commit and push verified checkpoints.
Earlier draft PRs remain unmerged.
