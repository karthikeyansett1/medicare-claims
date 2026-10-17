# Step 3 — Load the raw warehouse layer

Status: locally verified; user approved the Step 3 GitHub push.
Branch: `step-03-bronze`, based on Step 2. Earlier pull requests are not merged
by this step.

## What we are doing

Load the eight verified source CSVs into five PostgreSQL tables:
`bronze.beneficiary`, `bronze.inpatient`, `bronze.outpatient`, `bronze.carrier`,
and `bronze.pde`. The three beneficiary years share one table; carrier A and B
share one table. Every source column is TEXT. Column names are lowercase;
source field values, leading zeroes, empty strings, and negative amounts remain.

Each row gets `_sample_id`, `_source_file`, `_loaded_at`, and `_file_year`.
File year applies to beneficiary records and is NULL for the multi-year claims
files. Source SHA-256 hashes are recorded in the reconciliation report.

## Why we are doing it

Bronze is the recoverable source layer. Loading everything as text keeps unusual
values visible instead of failing or silently changing them during conversion.
Recording file lineage lets us trace a database row back to the source sample,
file, and load. Comparing database counts and monetary sums to the independent
Step 2 profile checks that loading did not omit or multiply records.

The loader streams CSV bytes through psycopg's `COPY FROM STDIN`, avoiding
row-by-row SQL inserts and avoiding a requirement to copy input files into the
Docker container. Source blanks are explicitly preserved using `FORCE_NOT_NULL`.

## How to explain it if asked

“I created a raw PostgreSQL layer with five tables, preserving every source
field as text and stamping each row with sample and file lineage. I used COPY
for bulk loading, then reconciled file-level counts and financial totals to my
source profile. The entire refresh is one transaction: if a file or validation
fails, the previous completed load remains intact.”

If asked why UNLOGGED: “These raw tables are rebuildable from verified source
files, so I used UNLOGGED storage. It reduces write-ahead logging, but after a
crash PostgreSQL may truncate those tables. I retain the source files and a
rebuild command, and I do not claim that bronze is crash-durable.”

If asked whether this cleans data: “No. Segments, missing codes, empty fields,
and negative payments remain. Cleaning and typed models belong in silver.”

## Load controls

- Verify all eight files against both the acquisition manifest and the profile
  before connecting for a load; reject header or source-identity mismatches.
- Recalculate each hash while streaming to detect changes during transmission.
- Use one transaction for creation or replacement of all five project tables.
- Reruns use transactional TRUNCATE, not append. Do not drop tables or use CASCADE.
  Unexpected existing schemas are rejected without an automatic migration.
- Take an advisory lock to prevent two instances of this loader refreshing the
  same schema concurrently. A lock timeout avoids waiting indefinitely for tables.
- Verify COPY row counts, grouped database counts, file/year/sample lineage,
  timestamps, raw TEXT types, UNLOGGED status, and profiled monetary sums.
- ANALYZE each table after loading so PostgreSQL has planner statistics.
- Write reconciliation evidence only after the database transaction succeeds.

## Reproduce

```sh
make db-up
make bronze         # acquire/verify cached files, then refresh all five tables
make verify-bronze  # read-only database checks against the current source profile
make test           # offline tests; database tests are explicitly skipped
make test-db        # all tests, including temporary PostgreSQL schemas
```

The current loader targets the fully profiled Sample 1 inputs. `DATA_DIR` can
point to a different project-local data root, but its paths, hashes, headers, and row
counts must also be represented in the manifest and profile. Arbitrary fixture
files are not silently accepted as verified full data. Sample 2 support will be
added with its corresponding source profile and reconciliation expectations.

`make bronze` replaces the five bronze table contents as one unit. It keeps the
previous committed contents if an ordinary load or check fails. This transaction
protection does not change the separate UNLOGGED crash-recovery limitation.

## Full-load results

| Table | Rows loaded | Difference from source |
| --- | ---: | ---: |
| bronze.beneficiary | 343,644 | 0 |
| bronze.inpatient | 66,773 | 0 |
| bronze.outpatient | 790,790 | 0 |
| bronze.carrier | 4,741,335 | 0 |
| bronze.pde | 5,552,421 | 0 |
| Total | 11,494,963 | 0 |

All eight file-level counts match, and all 56 checked per-file financial column
sums match Step 2. No financial checks were skipped. The initial verified load
finished in 38.35 seconds on this machine; this is one observed local run, not a
benchmark against another loading approach.

## Verification evidence

See [bronze reconciliation](../bronze_reconciliation.md) and its JSON companion.

- `make bronze`: passed; all 11,494,963 rows committed.
- `make verify-bronze`: passed through a fresh connection, confirming the committed
  contents and all 56 financial column sums in 7.73 seconds.
- `make test-db`: 34 tests passed, including six isolated live database cases.
- `git diff --check`: passed.
- Raw source files and local credentials remain excluded from Git.
The integration tests use unique `test_bronze_*` schemas and remove those schemas
afterward. They do not truncate or modify the real `bronze` tables.

The tests cover raw blank/leading-zero/whitespace preservation, metadata,
rereading and rerunning without duplicate rows, whole-batch rollback after a
malformed CSV, row-count mismatch, financial mismatch, changed streamed hashes,
and rejection of unexpected existing table columns.

## User review and publication

Push approval: user explicitly answered “yes” to the Step 3 push request.
This applies only to Step 3. The review base is `step-02-profile` while PR #2
remains open. Earlier pull requests are not merged by this publication.
Commit message: `Step 3: bronze load into Postgres with COPY, lineage columns, row-count reconciliation`.

## Technical references

The implementation follows [PostgreSQL 16 COPY](https://www.postgresql.org/docs/16/sql-copy.html)
and [psycopg block COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html).
The [PostgreSQL table documentation](https://www.postgresql.org/docs/16/sql-createtable.html)
describes the UNLOGGED recovery tradeoff.
