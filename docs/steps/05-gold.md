# Step 5 — Gold star schema

Status: locally verified; user approved the Step 5 GitHub push.
Branch: `step-05-gold`, based on published Step 4. Step 5 publication is approved.

## What we are doing

Create nine gold models: member, member-year, provider, and calendar dimensions;
professional line, inpatient episode, outpatient claim, and prescription facts;
and a member-year cost and utilization summary. The CCS dimension belongs to
Step 8, when its seed and mapping coverage are verified.

Each model states its grain, and every column has a dbt description. Primary
keys, member relationships, provider relationships, dates, costs, and enrollment
retention are tested. The office E&M seed is an exact copy of the earlier
reference file and receives explicit text typing and uniqueness tests.

## Why we are doing it

Facts and dimensions provide one consistent interface for later attribution,
metrics, the dashboard, and the assistant. Sample-aware keys prevent collisions
as more samples are added. Clear grains prevent accidental duplicate joins.
The member-year summary aggregates each fact separately before combining them,
so two professional lines and three prescriptions do not become six joined rows.

## How to explain it if asked

“I built a dimensional layer with documented grains and sample-aware keys. It
keeps detailed facts for investigation and a reconciled member-year summary for
provider attribution. I aggregate each claim type independently, then combine the
member-year totals. I test both totals and keys, and independently reconstruct
every member-year measure in Python to detect costs assigned to the wrong member
or year even when global totals still match.”

If asked about financial scope: “Medical Medicare paid includes inpatient,
outpatient, and professional payments. Prescription gross cost is a different
concept, so I retain it separately instead of calling the combined amount
Medicare paid.”

If asked about outside-window claims: “The calendar extends to actual source
dates, including 2007. I retain cost years without enrollment and label them
explicitly. Later analysis can restrict its population without making raw money
disappear from warehouse reconciliation.”

## Important decisions

- Provider identity is sample plus observed synthetic NPI, with explicit rendering
  and inpatient-attending roles. No names or specialties are inferred.
- `dim_member` uses the latest available annual demographics; historical fields
  remain in `dim_member_year`. Death date uses the earliest nonblank observation.
- Chronic-condition count is unknown if any of the eleven source flags is unknown.
- Inpatient attending NPI comes from the same canonical source segment as its
  admission, facility, DRG, and diagnosis. The join is tested for count preservation.
- Date/year assignment and all financial scopes are defined once in
  [measure definitions](../measure_definitions.md). Unknown dates have an explicit
  retained summary bucket. Enrollment-only years also remain, with zero events.
- `medical_paid_amt` never includes prescription gross cost or carrier allowed.
- Facility sums and conflict flags survive; this step does not declare conflicting
  episodes clinically eligible for readmission measurement.

## Indexes and performance verification

Gold model configs create B-tree indexes on keys and common join/filter columns,
including member_id on facts, member_key for sample-aware joins, rendering NPI
plus service date, and member/year lookups. Models run ANALYZE after materializing.
Index presence, columns, uniqueness, and validity are independently checked.

The reproducible index experiment copies the professional join columns and
member dimension into a uniquely named temporary schema, compares the same
provider/year join before and after indexes, checks identical results, and removes
the schema. It uses warm-ups and three measured runs per condition. It does not
remove working gold indexes or claim that every query benefits from indexing.
The copied tables are narrower than the full fact, and results are local, not
production benchmarks. [Measured results](../gold_index_benchmark.md): median 235.068 ms before indexes
and 27.686 ms after, with identical results for 20,867 matching lines. The
experiment retained all 9,388,987 professional rows and 116,352 members in its
copies. All temporary benchmark tables were removed.

## Reproduce

```sh
make gold
make verify-gold
make benchmark-gold
make dbt-docs
make test-db
```

The gold build assumes the verified silver layer already exists. `make gold`
validates the E&M seed, builds gold models, and runs their dependent tests. The
Python verifier currently targets the default local gold/silver schemas.
The entire dbt graph is not one atomic database transaction; downstream users
must wait for successful build and reconciliation before querying a refresh.

## Verification results

- Gold build: **9 models, 37 data tests, and 1 unit test passed**, with no errors
  or skipped nodes; observed local run time was 133.82 seconds.
- E&M seed: **10 rows**, exact reference bytes and expected code set, with
  **2 additional data tests passed**.
- Independent audit: **53/53 checks passed**, including **5,853,015 individual
  member-year field comparisons**, full gold column documentation, and all
  configured index columns/uniqueness/validity.
- Python regression suite: **34 passed**, none skipped.
- dbt catalog and lineage documentation generated successfully.

| Gold table | Rows |
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

Medical Medicare paid totals **$1,278,388,580**, split across the three medical
facts. Gross prescription cost is **$340,943,210** and patient prescription
payment is **$57,238,770**, reported separately. Carrier allowed charges are
**$534,585,890**, also separate. All scopes reconcile to silver.

The summary retains **504 member-years in 2007** carrying **$3,114,030** of
medical paid, plus **147 undated member buckets** carrying **$392,320**. The
undated bucket comes from **278 outpatient claims lacking a service date**.
There are **41,248 enrollment-only member-years with no claim events**. Neither
missing dates nor absent annual enrollment causes money to disappear.
The calendar spans 2007-11-27 through 2010-12-31.

An initial independent audit overlapped an E&M seed refresh and detected a
transient empty-seed snapshot. The completed-state audit then passed all checks.
Run verification only after all dbt writes finish; do not run it concurrently
with a refresh. This is part of the warehouse's documented refresh limitation.

See [build evidence](../gold_build_verification.json),
[reconciliation summary](../gold_reconciliation.md),
[individual checks](../gold_reconciliation.json), and
[index experiment](../gold_index_benchmark.md).

## Actual lineage

The screenshot below is from the generated dbt Docs graph. It shows the current
bronze, staging, silver, seed, and gold dependencies. Marts will appear when
implemented in later checkpoints. Test nodes are hidden for readability.

![Actual dbt lineage through gold](../img/step-05-dbt-lineage.jpg)

## User review and publication

Step 4 was approved and published in [draft PR #4](https://github.com/karthikeyansett1/medicare-claims/pull/4).
The user explicitly approved the Step 5 GitHub push after reviewing the completed
checkpoint. The draft PR targets `step-04-silver` while PR #4 remains open.
This approval does not merge earlier pull requests or authorize future pushes.

## Technical references

[dbt Postgres index configuration](https://docs.getdbt.com/reference/resource-configs/postgres-configs)
creates indexes within model materialization. PostgreSQL's
[EXPLAIN guidance](https://www.postgresql.org/docs/16/using-explain.html) and
[index examination guidance](https://www.postgresql.org/docs/16/indexes-examine.html)
support measuring actual planner choices after ANALYZE; an index does not force
or guarantee an index scan for every workload.
