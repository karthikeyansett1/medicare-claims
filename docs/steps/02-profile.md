# Step 2 — Understand the raw data

Status: locally verified; user approved the Step 2 GitHub push.
Local branch: `step-02-profile`, based on `step-01-data`. Step 1's draft PR is
still open; it has not been merged by this step.

## What we are doing

Read the CMS codebook and compared its field definitions with the actual headers.
Built `ingest/profile_raw.py` to scan all eight Sample 1 files in pandas chunks,
count exact event keys on temporary disk, and produce a readable Markdown report
plus a detailed JSON profile. This step does not modify the CSVs or load Postgres.

The profile covers row counts, distinct beneficiaries and event IDs, per-column
missingness, date ranges and validity, diagnosis mapping coverage, carrier line
structure, provider missingness, facility segments, payment totals, enrollment,
and records whose dates need review.

## Why we are doing it

We need to know what a row represents before joining tables or calculating cost.
One facility claim can occupy multiple rows, and one carrier row can contain
13 lines. Summing at the wrong level can overstate cost; dropping slots just
because a code is missing can understate it. Measured source counts also give us
an exact target for verifying the database load in Step 3.

## How to explain it if asked

“Before modeling claims, I profiled the complete source files and checked the
codebook against their headers. I measured missing values, repeated claim keys,
payment totals, date anomalies, and diagnosis mapping coverage. I processed the
large files in chunks and kept exact keys on disk so duplicates spanning chunks
would still be detected. That gave me an evidence-based grain and reconciliation
baseline before building the warehouse.”

If asked about a concrete correction: “The build guide treated outpatient rows
as whole claims, but the codebook and CSV include segments. It also combined
prescription gross cost with Medicare paid amounts. I documented both distinctions
so the later warehouse won't silently double count or mix financial definitions.”

## Findings to remember

- Scanned 11,494,963 rows; every file's row count matches CMS's published count.
- A nonblank-HCPCS-only carrier filter would discard $20,695,070 in payments.
- Found 68 inpatient and 10,975 outpatient claims spanning multiple segments.
- Found 2,621 negative facility payment values; they remain in the source totals.
- No invalid nonblank dates or services starting after recorded death were found.
- Keep prescription gross cost separate from medical Medicare-paid amounts.

A concrete interview explanation: “My profiling caught a proposed procedure-code
filter that would have removed $20.70 million in source payments. I documented
that payment-bearing lines must survive the unpivot even when the procedure code
is missing, so the eventual model can reconcile to the source.”

## Verification

- Full-source report: [data profile](../data_profile.md).
- Exact counters and source SHA-256 provenance: `docs/data_profile.json`.
- Method and source definitions: [interpretation notes](../profile_interpretation.md).
- Regression tests: invalid calendar dates, exact cents, payments without HCPCS,
  missing rendering NPIs, duplicates across chunks, repeated versus differing
  segment payments, and preservation of literal code values such as `NA`.
- `make test`: all 22 tests passed, including the 17 acquisition tests.
- All eight measured row counts match CMS Table 2; all input hashes match the manifest.
- The complete scan finished in 161.24 seconds on this local machine.
- A focused facility follow-up reproduced the full run's counters and explained
  which header fields disagree across segments.
- Final report checks confirm carrier totals split exactly into HCPCS-present
  and HCPCS-missing payment amounts; each date's valid, invalid, and blank counts
  reconcile to its file's row count.

## Reproduce

```sh
make setup
make profile
make test
```

`make profile` checks source hashes before scanning, writes the Markdown and JSON
reports, and fails if any row count differs from CMS's published Sample 1 counts.
It uses temporary SQLite files for exact distinct keys and claim-segment grouping;
those temporary files are removed at completion. Report timestamps and elapsed
time vary; analytical counters are deterministic for unchanged source data.

## User review and publication

Push approval: user explicitly answered “yes” to the Step 2 push request.
This approval applies only to Step 2. The review base is `step-01-data` while
Step 1 PR #1 remains open; neither pull request is merged by this action.
Commit message: `Step 2: raw data profile, file grain, and documented quirks`.
