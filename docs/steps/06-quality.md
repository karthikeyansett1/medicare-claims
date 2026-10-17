# Step 6 — Data-quality checks

## What we are doing

Add dbt-utils 1.4.1 and explicit checks for member foreign keys, member-year
natural-key uniqueness, source sex codes, diagnosis claim types, ordered dates,
and diagnosis-to-member relationships. Keep the earlier grain, casting,
financial reconciliation, enrollment, and gold dimensional checks in the full
build. CMS DE-SynPUF codebook BEN-4 defines sex codes 1 and 2; these synthetic
codes do not support population-level inference.

Add four warning monitors: events starting more than 30 days after death,
missing service dates, negative medical payments, and conflicting facility
headers. The death rule uses the gold member dimension's earliest observed
death date and the same service-date convention as cost attribution. It is a
screen, not clinical adjudication. A five-case fixture verifies the exact
30-day boundary, the first day beyond it, an earlier date, and null dates.

Install SQLFluff with its dbt templater and format the SQL models. The configured
rules cover layout, capitalization, explicit aliases, and null/not-equal
comparisons. All model SQL is linted after dbt expansion; macro definitions and
fixture inputs are not separately linted. Parsing and compilation errors are
not suppressed. Locked dependencies make these checks reproducible.

## Why

A key or amount mismatch can invalidate downstream rankings, so structural and
reconciliation failures stop the build. A known source irregularity needs
visibility and a documented interpretation. Dropping negative adjustments or
undated claims to make a test green would change reconciled payments. Warning
counts are evidence to review, not permission to ignore new changes in data.
Missing dates cannot pass a timeliness interpretation merely because SQL's
comparison returns null; the separate missing-date monitor makes them visible.

Existing safe-cast checks reject nonblank chronic-condition codes outside 1/2;
typed boolean outputs cannot represent other values. Null remains unknown.
CCS coverage and attribution-sum checks belong to Steps 8 and 7 respectively,
when those models exist. They are not included in this checkpoint's test count.

## How to explain it if asked

“I built quality checks around both the warehouse contracts and the source's
limitations. Broken keys, invalid codes, date order, or unreconciled amounts
stop the build. Source anomalies are retained and counted as warnings so the
analysis stays reproducible. I tested the death-date rule at its boundary,
linted the dbt SQL, and independently rechecked the financial totals after the
full rebuild. These are historical synthetic claims, so this validates the
pipeline rather than establishing clinical performance.”

## Reproduce verification

```sh
make setup
make sql-lint
make quality-build
# Wait for all warehouse writes to finish before reconciliation.
make verify-silver
make verify-gold
make test-db
```

On a fresh checkout, run `make dbt-deps` before `make sql-lint`. The existing
bronze source tables must already be loaded. `make quality-build` installs the
locked dbt package and builds all implemented models, seeds, and tests.
See [verification results](../quality_verification.md) and
[machine-readable evidence](../quality_verification.json).

## Review and publication

Step 5 is published in [draft PR #5](https://github.com/karthikeyansett1/medicare-claims/pull/5).
Step 6 is verified on `step-06-quality`. On October 10, 2026, the user authorized
committing and pushing each verified step and continuing the project without
further approval prompts. This supersedes the earlier per-push approval workflow.
Earlier draft pull requests remain unmerged. No release tag is created while
the dependent branches are still awaiting review.

## References

[dbt-utils package](https://hub.getdbt.com/dbt-labs/dbt_utils/latest/),
[dbt data tests](https://docs.getdbt.com/reference/resource-properties/data-tests),
and [SQLFluff dbt templater](https://docs.sqlfluff.com/en/stable/configuration/templating/dbt.html).
