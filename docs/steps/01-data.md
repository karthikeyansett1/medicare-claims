# Step 1 — Acquire and verify source data

Status: locally verified; user approved the Step 1 GitHub push.
Publication branch: `step-01-data`. See GitHub branch history for the published commit.

## What we are doing

Downloaded all eight Sample 1 CSVs: beneficiary files for 2008, 2009, and 2010,
inpatient, outpatient, both carrier parts, and prescription drug events.
Downloaded three CMS documentation PDFs and the AHRQ single-level CCS files.
Created the 10-code office E&M reference list.

Added a reproducible downloader and URL catalog, an integrity manifest, offline
verification, source documentation, and tests. Large source archives and claims
CSVs remain local; code, metadata, small references, tests, and notes are the
proposed GitHub changes.

## Why we are doing it

Provider measures depend on files belonging to the same beneficiary sample.
The current CMS page has a mislabeled 2010 link that would silently mix Sample 20
with Sample 1. Checking the exact sample token and the extracted filename catches
that error before modeling. Recording hashes and source URLs lets us identify
changed or damaged inputs later. Reusing verified local files avoids unnecessary
downloads.

## How to explain it if asked

“I built a repeatable acquisition pipeline for eight synthetic Medicare files.
I validated the file identities, archive integrity, and SHA-256 hashes before
accepting them. I found that CMS's Sample 1 page linked to Sample 20 for 2010.
I recovered the original Sample 1 file from a dated archive of CMS and verified
that all its beneficiary IDs belonged to Sample 1. I documented the provenance
so the workaround is transparent and reproducible.”

If asked about scope: “This checkpoint verifies source acquisition. Detailed
claims profiling, data cleaning, and provider metrics come in later steps.”

## Verification results

| Check | Actual result |
| --- | --- |
| Sample 1 completeness | 8 source ZIPs, 8 extracted CSVs |
| Compressed Sample 1 size | 379,065,352 bytes |
| Extracted Sample 1 size | 3,119,692,771 bytes |
| Manifest | 24 records covering downloads and extracted source files |
| Archive checks | All ZIP members passed CRC and expected filename checks |
| Offline integrity | `make verify-data` passed for all configured artifacts |
| Beneficiary unique IDs | 2008: 116,352; 2009: 114,538; 2010: 112,754 |
| Beneficiary sample consistency | Zero 2009 or 2010 IDs outside the 2008 population |
| Beneficiary keys | No blank or duplicated IDs within each annual file |
| CCS diagnosis map | 15,072 unique nonblank diagnosis codes; one blank-code placeholder retained |
| E&M reference | Exactly 10 distinct codes in the intended historical ranges |
| Automated tests | `make test`: 17 passed |
| Cache reuse | Second download run reused the previously verified files; offline verification made no network requests |

Test cases cover Sample 1 versus 10/20 confusion, redirects to the wrong sample,
unsafe ZIP paths, changed cached bytes, incomplete responses, HTML masquerading
as a PDF, bad CSV headers, and offline cache reuse.

Evidence: `docs/download_verification.json`, `docs/source_validation.json`, and
`data/manifest.csv`. The source dates and archived-file decision are documented
in `docs/data_sources.md`.

## How to reproduce

```sh
make setup        # installs the locked dependencies
make download     # downloads missing files; verifies cached files
make verify-data  # verifies locally without network requests
make test         # offline downloader tests
```

Run acquisition commands one at a time. Failed downloads never become final
files; a rerun starts the failed file again. If a cached file fails its hash
check, investigate it, then remove that specific corrupt local file and rerun
`make download`. Hash changes are rejected against the recorded manifest.

## Limits and next step

Sample 2 is deliberately deferred until the Sample 1 pipeline works end to end.
No claims were loaded into PostgreSQL. These checks do not yet establish date
validity, claim-level uniqueness, payment reconciliation, or attribution quality.
Step 2 will profile all file types and document those quirks.

## User review and publication

User review: checkpoint results presented; user approved publication.
Push approval: user explicitly answered “yes” to the Step 1 push request.
This approval applies only to Step 1.
Commit message: `Step 1: download pipeline, file manifest, CCS and E&M reference files`.
