# Step 4 — Typed staging and silver models

Status: locally verified; user approved the Step 4 GitHub push.
Branch: `step-04-silver`, based on `step-03-bronze`. No preceding PR is merged.

## What we are doing

Build five staging tables and seven silver tables with dbt on PostgreSQL. Staging
keeps the source grain and all source columns, trims blanks to NULL, preserves
identifiers as text, converts dates/numbers, and maps chronic flags 1/2 to true/false.
The explicit column contract is in `dbt_project/dbt_project.yml`.

Silver produces carrier lines, diagnosis positions, inpatient claim episodes,
outpatient claims, annual beneficiary enrollment, prescription fills, and a
cast audit. File, sample, and load lineage remain available throughout.

## Why we are doing it

Typed dates and exact decimals make calculations predictable. Explicit grains
prevent accidental duplicate joins. Reconciliation checks establish that typing,
unpivoting, and segment aggregation preserve counts and money. A reproducible
dbt graph makes dependencies and validation visible before gold metrics are built.

## How to explain it if asked

“I used dbt to turn raw claims into typed, traceable tables. I preserved source
rows in staging, expanded the carrier's 13 slots into service lines, and grouped
facility segments using sample, member, and claim IDs. I tested table grains and
reconciled exact monetary totals through each layer. Conflicting segment headers
and missing provider codes remain explicit instead of disappearing in cleaning.”

If asked about missing HCPCS: “A code-only filter would have dropped $20,695,070
of synthetic carrier payments. I kept slots with activity, including payment or
allowed charges, and flagged missing codes and rendering NPIs for later analysis.”

If asked whether episodes are validated clinical stays: “They are initially
claim-based episodes. I choose the lowest source segment's header and expose
conflicts. Different claim IDs are never merged just because admission date and
facility match. Readmission eligibility will explicitly handle conflicts in Step 9.”

## Modeling decisions

- Safe dates validate the actual calendar, including leap years; an eight-digit
  shape alone is insufficient. Malformed nonblank dates/numbers/flags become NULL,
  their source column names remain in `_cast_error_columns`, and a failing dbt
  test prevents accepting a build with conversion losses. Bronze preserves values.
- Safe numeric casts use exact unrestricted NUMERIC after a 30-character syntax
  guard. They do not silently round to cents. Integers accept up to nine digits;
  codes, identifiers, and segment-independent diagnosis strings remain text.
- Carrier activity follows the Step 2 definition: a code, NPI, line diagnosis,
  nonzero Medicare payment, or nonzero allowed amount. Zero-only empty slots are
  excluded. Other slot attributes remain in staging; this is an analytical line
  definition, not a count of encounters. A full-data audit found zero excluded slots with nonzero
  deductible, primary-payer, or coinsurance amounts; those sums are also tested.
  The unpivot uses a lateral VALUES list
  to scan the wide table once instead of 13 separate UNION scans.
- Facility grain is `(sample, member, claim)`. Payments are sums of all source
  segments, including equal and negative values. Equal payment is a diagnostic,
  not proof of duplication. Canonical header fields come together from the lowest
  segment; admission/facility/principal diagnosis/DRG/discharge conflicts are
  flagged. Service bounds are earliest claim-from/latest claim-through.
- Outpatient ED is true if any segment has an HCPCS code 99281–99285 in any of its
  45 slots. This is a project proxy; it is not a revenue-code-based ED definition.
- Diagnosis grain includes claim type, segment, and position. All nonblank claim
  diagnosis positions survive; carrier line diagnoses remain on carrier lines.
  Codes are uppercased and decimal points removed only in the normalized column;
  `source_dx_cd` retains the trimmed source representation. No CCS mapping yet.
- `silver_member_months` contains **one row per member-year**, not one per calendar
  month. Age is at January 1. Strict full-year FFS requires A=12, B=12, HMO=0.
  The additional death-adjusted proxy requires A and B annual counts at least the
  death month (and at most 12), HMO=0; deaths before the year are ineligible.
  Missing enrollment never automatically qualifies a member; eligibility may
  remain NULL.
  Annual counts do not prove that A/B coverage overlaps or runs through death.
  `required_months` is a screening threshold, not observed covered person-time.
  Final quality observation windows and denominator rules remain later steps.
- PDE gross drug cost and patient pay stay separate from medical Medicare paid.
  No combined “total Medicare paid” measure is created.

## Execution and limitations

```sh
make dbt-debug
make silver
make verify-silver
make test-db
```

The Python runner reads `.env` with python-dotenv and passes the password through
`DBT_ENV_SECRET_PG_PASSWORD` for dbt log redaction. It does not execute `.env` as
shell code. Credentials, compiled SQL, dbt logs, and target artifacts are ignored.
The local project uses literal `staging` and `silver` schemas. Set dbt's
`schema_prefix` and `bronze_schema` vars for separate dbt environments. The
Python reconciliation command currently targets the default local schemas only.
Developers must not rebuild the same schemas concurrently.

Each dbt table rebuild is transactional, but the entire DAG is not one database
transaction. A failed build can leave a mix of model generations: downstream use
must wait for a successful build and reconciliation. These are local checks;
CI/CD arrives in Step 15. Source bronze is not modified by `make silver`.
The reserved gold/marts configuration currently produces two unused-folder
warnings because those later layers have no models yet.

## Verification results

The final `make silver` run succeeded: **12 models, 19 data tests, and 5 unit
tests**, with no errors or skipped nodes. It took 262.17 seconds on this machine;
this is one observed run, not a comparative performance benchmark.

`make verify-silver` passed **146/146** independent checks in 64.73 seconds.
All five staging row counts match bronze and the source profile, all checked
numeric totals survive typing, all silver financial totals reconcile, and
there are **zero nonblank cast failures** across the eight files.

| Silver model | Rows |
| --- | ---: |
| Carrier lines | 9,388,987 |
| Diagnosis positions | 12,733,072 |
| Inpatient claim episodes | 66,705 |
| Outpatient claims | 779,815 |
| Member-years | 343,644 |
| Prescription fills | 5,552,421 |
| Source-file cast audit | 8 |

The checks retain all **372,680** nonzero-paid carrier slots without HCPCS,
including their **$20,695,070** in payments. There are **68** inpatient and
**10,975** outpatient episodes with conflicting headers. All are retained and
flagged. There are 62,595 outpatient claims meeting the stated ED proxy.

The independent enrollment report shows strict/death-adjusted screening counts
by year; these remain proxies and must not be presented as validated member-month
exposure. No provider rankings or clinical performance measures are claimed yet.

`make test-db` passed all **34** Python regression tests, including the six
isolated database cases. Whitespace and credential-literal checks passed.

See [build and test evidence](../silver_build_verification.json),
[reconciliation summary](../silver_reconciliation.md), and
[all individual reconciliation checks](../silver_reconciliation.json).

The unit fixtures cover invalid calendar dates and amounts, flag conversion,
leading-zero identifiers, nonblank conversion auditing, blank-HCPCS paid lines,
negative payments, equal-payment segments, conflicting headers, distinct claims
sharing admission/facility, ED codes on later segments, and annual death rules.
Initial dictionary fixtures exposed the adapter's ARRAY typing limitation;
explicit SQL fixtures resolved it. Final verification has no failed fixtures.

## User review and publication

The user explicitly approved the Step 4 push and continuing to Step 5.
This publication approval applies only to Step 4. The review base is
`step-03-bronze` while PR #3 remains open.
Earlier pull requests will not be merged as part of publication.

## References

- [dbt Postgres profile](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup)
- [dbt schema generation](https://docs.getdbt.com/docs/build/custom-schemas)
- [dbt environment variables](https://docs.getdbt.com/reference/dbt-jinja-functions/env_var)
- [Measured source findings and clinical limitations](../profile_interpretation.md)
