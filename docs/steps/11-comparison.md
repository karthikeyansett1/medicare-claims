# Step 11 — attribution-method sensitivity

## What changed and why

Added reproducible comparison code, 30 sample/year/threshold/metric aggregate
rows in `analysis.method_comparison`, CSV exports at provider level or above,
three static charts, and a cohort-and-service trace of the greatest PMPM mover.
The findings quantify the effect of a definition change without implying real
provider performance. No member-level rows are exported. Only Sample 1 is loaded;
the code partitions by sample and year and never treats NPI alone as global.

## Exact analysis policy

- Coverage denominator: every eligible member-year in each sample/performance
  year. Reassignment denominator: members attributed under **both** methods;
  numerator: differing NPIs. Neither new B-only coverage nor the unattributed
  population is mislabeled reassignment.
- Compare A/B separately for medical PMPM, O/E, and readmission rate; compare
  PMPM/O/E within each method. Repeat every comparison at panels 10/20/30.
  Medical paid excludes Rx gross drug costs. Readmission denominators count
  index episodes; null/zero denominators yield unavailable rates, not zero.
- First filter each method/metric to qualifying panels and nonmissing finite
  values. Rank and decile within that full sample/year/method/metric population;
  **then** intersect provider identifiers. Raw/OE comparisons likewise intersect
  available metrics. Invalid O/E cannot remove a valid PMPM from its own ranking.
  Current live minimum-20 PMPM/OE populations match the operational mart exactly.
- Display ranks use `row_number` ordering by metric ascending then NPI ascending.
  Deciles match PostgreSQL `ntile(10)` with the same ordering; larger values
  mean higher cost/rate. Earlier buckets receive remainder rows. This can split
  identical values across deciles, particularly zero readmission rates; these
  are deterministic reporting groups, not clinically distinct groups.
- Spearman is computed on the **common cohort's raw scores**, with average
  tied-score ranks, not the tie-broken display ranks. Fewer than three pairs or
  constant input produces NULL plus an explicit reason. No inferential p-values
  are claimed for these synthetic populations.
- Top-decile sets include common-cohort providers whose independently computed
  decile equals 10. Jaccard is intersection/union. This excludes one-method-only
  providers from both sets; left/right qualifying counts expose that attrition.
  Empty union yields NULL with `empty_union`. If either qualifying population
  has fewer than ten providers, deciles, movement counts and Jaccard are
  unavailable with `too_few_qualifying_providers`; ranks still exist.
- Absolute decile movement bins are 0/1/2/3+. They retain each method's original
  reference population, rather than re-decile only the intersection. Threshold
  sensitivity recomputes all ranks/deciles from scratch, never filters the
  mart's already-computed 20-member ranks.
- The greatest mover is selected at threshold 20 across sample/year by absolute
  PMPM-decile change, then absolute rank change, then ascending sample/year/NPI.
  Export incoming, outgoing and retained cohort aggregates, and all their
  professional lines grouped by HCPCS. Costs are member-year totals, never
  sums joined to line facts that would multiply payments.
- The waterfall covers **all audit years**, including the out-of-performance-
  year exclusion. Exclusions are mutually exclusive first reasons from Step 9;
  their sum plus eligible episodes reconciles to the full episode table.

The summary table grain is `(sample, year, min_panel, comparison)` with a primary
key. `movement_3` means 3+; fractional columns are 0–1, not percentages. Coverage
fields repeat across metrics/thresholds for dashboard convenience: **do not sum
these duplicated counts across comparison rows**. CSV empty cells represent
unavailable values; status columns explain why. Provider-pair exports identify
left/right by the comparison name: A/B or raw/OE as named.

## Verification and reproduction

```sh
make compare verify-comparison
.venv/bin/python -m pytest tests/test_compare_methods.py -q
RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/ -q
```

The independent verifier uses PostgreSQL window functions and Pearson correlation
of average tied-score ranks, rather than calling the Python ranking/comparison
functions. All 30 aggregate rows and 3,462 provider pairs passed: 14,208 SQL
numeric checks, 1,496 live mart rank/decile checks, both coverage groups, 30
persisted rows, both traced panels, three traced professional-service cohorts,
and all 64,560 waterfall episodes. Eight hand-constructed tests cover uneven
NTILE buckets, ties, thresholds before intersection, empty unions, unavailable
small cohorts, nulls/infinities, zero/null index denominators, reversed ranks and tied-score Spearman.
Seven additional verifier regressions exercise SQL finite-value filtering, empty and
small/asymmetric cohorts, constant inputs, empty top unions, rejection of false
status/zero outputs, and the mart's small-population deciles. SQL fixture tests
use isolated temporary tables, without modifying warehouse data. Direct mart
rank checks apply only to identical finite eligible reference populations; a
reported skip count exposes any mismatch. Current live data has **zero skips**.
The full database-enabled test suite passed **57 tests**. All 11 output files
were byte-identical on a repeat run against an unchanged warehouse. The generator
reads source data under a repeatable-read transaction; the summary replacement
commits atomically. `git diff --check` passed.

All three regenerated PNGs were visually inspected for text, axes and counts.
Dependencies add explicit SciPy and matplotlib requirements; lock resolution
retained all prior package versions and installed seven matplotlib packages.
Publication follows completed checkpoint review; no Step 12 work is included.

## How to explain it in an interview

“I separated coverage from reassignment, because a broader attribution rule can
assign previously unassigned people without moving an existing assignment. I
recomputed provider groups under each panel threshold and measured agreement
only among common providers. I matched the production decile policy, exposed
tie splitting, and independently checked the output in SQL. For the biggest
mover I traced panel composition: only three of 24 members remained, and the
incoming cohort's inpatient costs explained most of the dollar change. That
explains the arithmetic without inventing a clinical story.”

These results describe synthetic DE-SynPUF data. Annual enrollment counts are
proxies; readmissions lack planned-admission exclusion and clinical adjudication;
small index denominators can be unstable; provider specialty is not established.
The concurrent O/E model is descriptive, overpredicts aggregate cost by ~10–15%,
and is not a validated clinical risk model. No causal or real-provider conclusion
is supported.

## Implementation references

- [PostgreSQL window functions](https://www.postgresql.org/docs/current/functions-window.html)
- [SciPy Spearman correlation and constant-input behavior](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)
- [matplotlib Figure.savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html)
- [Measured findings and charts](../../analysis/findings.md)
- [Machine-readable verification](../../analysis/output/verification.json)

## Publication and next checkpoint

Published from `codex/step-11-comparison`, based on `codex/step-10-metrics`,
under the standing authorization for verified checkpoint commits and pushes.
Earlier draft PRs remain unmerged. Next is an additional Sample 2 integration
checkpoint before assistant implementation and evaluation against the final dataset.
