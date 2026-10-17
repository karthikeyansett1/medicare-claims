# Step 14 — Provider scorecard dashboard

## What and why

Atlas is a four-page Streamlit dashboard with offline, provider-level or higher
CSV extracts. Tableau is not installed on this Mac, so this checkpoint uses the
existing Python UI stack and produces working browser pages and screenshots.
There is no `.twbx` or `.pbix` workbook and no claim of Tableau implementation.
Public hosting is a later checkpoint; this step runs locally without database
credentials or API access after dependencies are installed.

## Run and refresh

```sh
make dashboard   # http://127.0.0.1:8502
make export      # refresh from the configured local warehouse
```

`analysis.export_dashboard` takes a read-only repeatable-read snapshot and
reuses Step 11's comparison implementation. It exports 872 ≥20-member provider
rows, eight all-panel population summaries, 820 condition categories across all
observed years, 60 comparison summaries, 6,991 common-provider pairs and four
coverage cohorts. The committed CSVs total about 1 MB and contain no member or
claim identifiers. Content hashes make data files deterministic; the manifest
records timestamp, samples, performance years, definitions hash and row counts.
Each CSV is staged and atomically replaced before the manifest is atomically
swapped. A failed refresh leaves the prior manifest usable. Old hash-named files
are retained, so a concurrent reader can finish its prior snapshot. Remove
unreferenced snapshots only when no dashboard readers depend on them.

## Reading the four pages

- **Overview:** all attributed eligible panels, including panels below 20. PMPM
  is total medical payment / total exposure months; utilization uses total events
  / total months ×12,000. Readmission rate uses total numerator / eligible index
  stays, never an average of provider rates. Coverage shows the eligible population
  separately from the attributed population.
- **Provider scorecard:** one sample/year/method, ≥20 members by default. NPI
  search preserves leading zeroes. Raising the display minimum does not recompute
  the mart's ≥20-reference ranks. Cost, expected cost and Rx gross are separate;
  sparse readmission denominators are visible beside the rate.
- **Method comparison:** all four sample/year cohorts and thresholds 10/20/30.
  PMPM, O/E, readmissions, and within-method raw/adjusted comparisons reuse the
  validated comparison exports. Ranks/deciles precede the common-cohort
  intersection. High-decile Jaccard uses common providers; Spearman is computed
  from their raw scores with average ranks for ties.
- **Conditions:** top 15 principal CCS categories by inpatient payment. This
  source mart pools all loaded samples, so the sample/method controls are
  disabled and the pooled scope is explicit. Category member counts overlap;
  never sum them. Inpatient payments are not total medical spending.

Every page reads its measure descriptions from the canonical assistant semantic
layer and offers the full measure definitions for download. These historical,
synthetic measures and concurrent GLM adjustment describe sensitivity; they are
not validated clinical quality ratings.

## Verification evidence

On October 12, 2026 (local time), five dashboard contract tests including live
warehouse reconciliation passed. Offline tests cover unequal-provider PMPMs,
index-stay weighting, empty cohorts, identifier privacy, content hashes and
leading-zero NPIs. A Streamlit application test covers four page paths, empty
search, threshold changes and disabled pooled controls. The final offline suite reported **110 passed / 19 skipped** (DB-dependent tests
are opt-in); the warehouse reconciliation test also passed when explicitly enabled.

Independent verification with database tests enabled passed **129 tests in
9.28 seconds**. All eight overview cohorts reconciled to the complete provider
mart, and all 12 sample/year/threshold reference-population comparisons passed.
Manifest integrity, extract privacy, and all four screenshot artifacts also passed
independent inspection.

Live CUA browser interactions verified all four pages, Method A→B, an empty NPI
search followed by `0221840958`, panel threshold 20→30, Sample 1→2, and condition year
2009→2010. Example Overview Sample 1/2009: Method A 57,247 members at $498.47
medical PMPM; Method B 62,839 at $462.83. Comparison shared providers changed
105→79 at threshold 20→30. Conditions 2010 showed $262,716,030 across 27,086
claim-based stays; sample/method controls were disabled.

Screenshots are native browser JPEGs (the browser API produces JPEG, not PNG):
[Overview](../img/dashboard-overview.jpg),
[Provider scorecard](../img/dashboard-scorecard.jpg),
[Method comparison](../img/dashboard-comparison.jpg),
[Conditions](../img/dashboard-conditions.jpg).
The viewport requires scrolling for lower tables and definitions; screenshot
views capture the primary metrics or charts. No paid model calls were made.

## Interview explanation

“I made the attribution rule visible as a decision that changes both patient
panels and provider reference populations. The overview uses weighted totals
across all attributed members, while the scorecard enforces a reporting minimum.
I deliberately disabled the sample filter on pooled condition data rather than
presenting a misleading sample-specific view. Hash-verified aggregate extracts
make the dashboard portable without exposing member records or requiring a live
warehouse.”

## Publication

Published in [draft PR #15](https://github.com/karthikeyansett1/medicare-claims/pull/15)
from `codex/step-14-dashboard`, based on `codex/step-13-eval`, under
standing checkpoint authorization. The dashboard uses verified aggregate extracts
and does not require paid API calls. Live assistant validation and evaluation remain
deferred by user request. Earlier draft PRs remain unmerged.
