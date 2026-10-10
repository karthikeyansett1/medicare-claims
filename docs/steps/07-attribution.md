# Step 7 — visit and allowed-cost attribution

## What we did

Built four gold tables: candidate evidence, Method A winners, Method B winners,
and their long union. Every eligible member year in 2009/2010 appears once per
method, including people with no qualifying provider. Assignments are sample-aware.
A uses distinct office E&M days, latest office date, then lowest NPI. B uses known
allowed sums across professional lines, distinct service days, then lowest NPI.
Missing allowed amounts are counted and omitted from sums; all-unknown candidates
are ineligible for B. A partially known total remains explicitly incomplete.

## Why

Attribution changes which provider is responsible for a member's measured costs
and outcomes. Deterministic rules and retained candidate evidence make those
changes explainable. Multiple billed lines should not become multiple office
visits. Unknown cost must not silently become zero. Unattributed members must
remain visible in the coverage denominator.

## Verification

Run `make attribution`, `make verify-attribution`, and
`.venv/bin/python -m ingest.run_sqlfluff lint dbt_project/models/gold/attribution*.sql`.
The targeted build has four models and 14 data tests. Four unit fixtures cover
multiple lines on one date, tie order, missing amounts, ineligible/out-of-year
members, sample collisions, and explicit unattributed rows. Python reconstructs
all winners directly from individual fact rows with sets and exact Decimal sums.
See [verification](../attribution_verification.md) and
[five reproducible spot checks](../../analysis/attribution_spot_check.md).
These checks are agent-verified, not human-verified.

## How to explain it in an interview

“I compared two retrospective provider attribution methods on the same eligible
population. One ranks distinct office visit days; the other ranks allowed cost.
I made tie-breaking deterministic and kept unattributed people in the denominator.
I retained candidate evidence and independently rebuilt every winner from fact
rows in Python, including five reproducible examples. These synthetic claims
lack reliable specialty, so I do not describe the result as primary care attribution.”

## Limitations and next step

Service dates are carrier claim-from dates, annual FFS eligibility is a screening
proxy, and unknown allowed amounts may change a cost-plurality assignment.
Provider panels below 20 remain in attribution but will be excluded from primary
provider performance reporting. Step 8 adds the validated ICD-9 CCS mapping;
no clinical grouping or primary care specialty is inferred here.

## Recorded results

Final targeted build: 4 models, 14 data tests, 3 unit tests; all passed, zero
warnings/errors/skips, 17.84 seconds. SQL lint passed all four new models.
`make test`: 30 passed, six database integration tests skipped by that offline
command. Independent verification reconstructed 272,074 assignments for 136,037
eligible member years from 4,031,994 fact lines with zero differences.

Coverage A/B was 78.75%/86.45% in 2009 and 72.36%/82.49% in 2010. Median panel
size is one across each year/method; only 84–121 provider panels meet the primary
≥20 threshold. That sparse synthetic distribution limits broad provider ranking
claims and must remain visible in the later comparison. Five complete trace
examples accompany the verification. See [build evidence](../attribution_build_verification.json).

### Review follow-up

Added a fourth dbt unit fixture proving that larger allowed totals win even when
the competing provider has more service days and a lower NPI. Separate cases
cover unequal positive totals, zero versus negative, and two negative totals;
each includes an all-unknown candidate with still more days and a lower NPI.
All four Step 7 unit tests passed in a separate targeted run (0.42 seconds).
The original full build evidence above remains unchanged; see
[follow-up unit evidence](../attribution_unit_followup_verification.json).

## Publication

Published in [draft PR #7](https://github.com/karthikeyansett1/medicare-claims/pull/7)
from `codex/step-07-attribution`, based on `step-06-quality`, under the
October 10 authorization to commit and push each verified checkpoint without
further prompts. Earlier draft PRs remain unmerged.
