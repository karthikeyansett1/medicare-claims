# Provider Performance Analytics on Medicare Claims

Build a reproducible warehouse of synthetic Medicare claims to compare provider
cost, utilization, and readmission rankings under two attribution methods.
Later checkpoints add a dashboard and an evaluated analytics assistant.

**Status: Step 3 bronze load committed and reconciled locally; publication approved.
All 11,494,963 source rows are present in five PostgreSQL bronze tables.**

## Work checkpoint by checkpoint

Each step includes implementation, verification evidence, and notes covering
what we did, why it matters, and how to explain it in an interview. We review
that checkpoint together before continuing. GitHub pushes require an explicit
yes for that specific step. Repository: [medicare-claims](https://github.com/karthikeyansett1/medicare-claims).
Future pushes still require separate approval.

See [the roadmap](docs/roadmap.md), [Step 0 notes](docs/steps/00-setup.md),
[Step 1 notes](docs/steps/01-data.md), and [the decision log](docs/decisions.md).

## Local setup

From this folder, with Docker Desktop running and uv installed:

```sh
cp .env.example .env
# Edit PG_PASSWORD in .env. Do not put real credentials in .env.example.
make setup
make db-up
make verify
```

Python 3.11 and dependencies must download successfully before setup is complete.
PostgreSQL is bound to localhost. Connection helpers load .env relative to the
project root, and existing environment variables take precedence.

The full `make all` pipeline will be added as its stages are implemented.
GitHub authentication is needed only for publication, not local development.
The local folder remains `Project 3`; the GitHub repository name is `medicare-claims`.

## Get and verify Sample 1

```sh
make download
make verify-data
make test
```

Source ZIPs and extracted claims use about 3.5 GB locally and stay out of Git.
The small reference files and `data/manifest.csv` are versioned. See
[source provenance](docs/data_sources.md) for the archived CMS 2010 file used
because the current Sample 1 link points to Sample 20. The manifest contains
locally calculated SHA-256 checksums, download times, and source URLs.

Acquisition checks passed for all eight CSVs, three CMS PDFs, and the CCS source
files. The downloader has 17 passing offline tests. Full data profiling is complete; see the report below.

## Raw data profile

```sh
make profile
```

The [full profile](docs/data_profile.md) covers 11,494,963 rows across all eight
files, with every count matching the CMS user guide. It identifies segmented
facility claims, negative payments, and $20,695,070 of carrier payments on slots
without procedure codes. Those findings guide the future warehouse models;
raw rows are now loaded in bronze without cleaning.

See [Step 2 notes](docs/steps/02-profile.md) for the explanation and verification,
and [profiling decisions](docs/profile_interpretation.md) for financial and grain
definitions. The Step 2 checkpoint passed 22 tests. Step 2 publication is approved on `step-02-profile`; future pushes need separate approval.

## Load and reconcile bronze

```sh
make bronze         # verify/acquire source files and refresh all five tables
make verify-bronze  # read-only reconciliation against the source profile
make test-db        # complete test suite, including isolated PostgreSQL tests
```

The load uses COPY in one transaction, preserves source field values as TEXT,
and adds sample/file/year/time lineage. A successful rerun replaces the five
tables rather than appending duplicates. A failed load rolls back the batch.
The tables are UNLOGGED and rebuildable; they are not crash-durable.

[Reconciliation results](docs/bronze_reconciliation.md) show zero row-count
differences and agreement across 56 per-file financial sums.
[Step 3 notes](docs/steps/03-bronze.md) explain the design and its verification.
Step 3 publication is approved on `step-03-bronze`; future pushes require separate approval.

The complete local suite now passes **34 tests**, including six database integration cases.
