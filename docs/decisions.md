# Decision log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-08 | Require explicit approval for each GitHub push. | User request overrides automatic push instructions in the guide. |
| 2026-10-08 | Build and review one guide checkpoint at a time. | Keep verification and explanations understandable. |
| 2026-10-08 | Use the existing Project 3 workspace. | Avoid an unnecessary nested repository or folder move. |
| 2026-10-08 | Bind PostgreSQL to localhost and retain default memory settings initially. | Verify resource needs before tuning per-query memory. |
| 2026-10-08 | Install dependencies incrementally and lock resolved versions. | Keep each checkpoint reproducible without installing unused packages. |
| 2026-10-08 | Validate guide methodology against source documentation before implementation. | Example code and recalled column names are not verified specifications. |
| 2026-10-08 | Verify psycopg and SQLAlchemy connections in make verify. | Live integration exposed a driver parameter mismatch that import checks could not catch. |
| 2026-10-08 | Publish Step 0 to karthikeyansett1/medicare-claims after verification. | User explicitly approved this push; later pushes still require approval. |
| 2026-10-08 | Start with Sample 1 and defer Sample 2. | Validate the pipeline end to end before scaling. |
| 2026-10-08 | Reject the current 2010 link to Sample 20 and use the 2017-05-29 archived original CMS Sample 1 file. | Current Sample 1 endpoints return 404; archived ZIP identity and beneficiary membership checks pass. |
| 2026-10-08 | Record hashes for source files and extracted files; verify before reusing cached files. | Detect corruption and preserve provenance across reruns. |
| 2026-10-08 | Preserve the unmodified 2015 ICD-9 CCS source and its blank-code placeholder. | Source acquisition should not silently make clinical mapping decisions. |
| 2026-10-08 | Start office E&M attribution candidates with 99201–99205 and 99211–99215. | Explicit historical visit definition; these codes do not prove primary care specialty. |
| 2026-10-08 | Publish verified Step 1 on step-01-data with a pull request. | User explicitly approved the Step 1 push; future checkpoints require separate approval. |
| 2026-10-08 | Preserve CSV bytes with Git attributes, including AHRQ source whitespace. | Line-ending conversion would break the recorded source hashes after cloning. |
| 2026-10-08 | Profile all eight files in chunks and keep exact event keys on temporary SQLite storage. | Bound working memory while detecting duplicate keys across chunks and carrier parts. |
| 2026-10-08 | Treat outpatient as segmented, like inpatient. | The actual header and CMS OP-3 include SEGMENT; one row is not necessarily one claim. |
| 2026-10-08 | Keep gross drug cost separate from medical Medicare paid. | CMS PDE-8 defines TOT_RX_CST_AMT as gross drug cost; labeling the combined amount Medicare paid would be misleading. |
| 2026-10-08 | Preserve blank-HCPCS payments and negative amounts during profiling. | Excluding them prematurely could break reconciliation or discard valid payment adjustments. |
| 2026-10-08 | Build Step 2 on the published Step 1 branch while its PR remains open. | Continue the approved local work without interpreting permission to profile as permission to merge. |
| 2026-10-08 | Preserve payment-bearing carrier slots even without HCPCS in later financial modeling. | Profiling found 372,680 such nonzero-paid slots totaling $20,695,070; filtering on HCPCS would lose those amounts. |
| 2026-10-08 | Use sample/member/claim as initial episode identity, retain segments, and flag conflicting headers. | Distinct claims can share admission/facility keys, and multi-segment headers disagree; clinical stay rules need explicit treatment. |
| 2026-10-08 | Retain all facility row payments as the source reconciliation baseline. | Equal amounts do not prove duplicates; most multi-segment groups have differing payments. |
| 2026-10-08 | Publish Step 2 with a pull request based on step-01-data while PR #1 remains open. | User approved this push; the dependent review shows only profiling changes and does not merge either step. |
| 2026-10-08 | Load all five bronze tables in one transaction, using COPY and UNLOGGED storage. | The layer is rebuildable; ordinary errors roll back the batch, while UNLOGGED crash recovery requires reloading. |
| 2026-10-08 | Preserve every source field as TEXT and use FORCE_NOT_NULL for CSV blanks. | Keep empty strings, identifiers, malformed values, and negative amounts visible before silver transformations. |
| 2026-10-08 | Replace project bronze contents with transactional TRUNCATE on reruns; reject schema drift. | Prevent duplicate loads without dropping tables or cascading into downstream objects. |
| 2026-10-08 | Reconcile per-file lineage and 56 financial column sums as well as row counts. | Verify that merging beneficiary years and carrier parts neither loses nor multiplies rows or payments. |
| 2026-10-08 | Keep Step 3 on a local branch based on Step 2 and require new push approval. | Continuing implementation does not authorize publication or merging earlier pull requests. |
| 2026-10-08 | Publish Step 3 with a pull request based on step-02-profile while PR #2 remains open. | User explicitly approved this push; the review isolates bronze loading and does not merge earlier steps. |
| 2026-10-09 | Build Step 4 locally on step-03-bronze; require separate publication approval. | The user authorized implementation, while preserving per-step push approval. |
| 2026-10-09 | Validate calendar dates and count nonblank conversion failures in dbt. | Pattern-only dates can be invalid; safe casts must not create silent data loss. |
| 2026-10-09 | Use exact NUMERIC values and reconcile all staged numeric amounts. | Prevent unnoticed rounding or losses during text-to-number conversion. |
| 2026-10-09 | Unpivot carrier slots with one lateral VALUES scan and retain the profiled activity definition. | Preserve missing-HCPCS payments and avoid 13 full-table scans. |
| 2026-10-09 | Select the lowest facility segment as a canonical header, retain sums, and flag conflicts. | A deterministic header is reproducible but does not establish clinical consistency. |
| 2026-10-09 | Retain diagnosis segment and position grain instead of flattening conflicting claims. | Keep all observed diagnoses without claiming they are independent diseases or encounters. |
| 2026-10-09 | Label death-adjusted FFS eligibility as an annual-count proxy. | Annual enrollment counts cannot establish the timing or overlap of covered months. |
| 2026-10-09 | Use explicitly typed SQL input fixtures for dbt unit tests. | The installed Postgres adapter renders an invalid ARRAY type for dictionary fixtures containing array columns. |
| 2026-10-09 | Accept Step 4 locally after 12 models, 24 dbt tests, 34 regression tests, and 146 independent checks pass. | Verify counts, cast failures, grains, and financial totals before requesting publication approval. |
| 2026-10-09 | Publish Step 4 with a draft PR based on step-03-bronze, then implement Step 5 locally. | The user approved this push and the next implementation step; Step 5 still needs its own publication approval. |
| 2026-10-09 | Preserve sample-aware member/provider keys throughout gold. | Avoid cross-sample collisions while retaining original text IDs. |
| 2026-10-09 | Aggregate each fact independently before combining member-year costs. | Prevent fact-to-fact fan-out and retain zero-event enrollment years. |
| 2026-10-09 | Keep medical Medicare paid, allowed charges, prescription gross cost, and patient payments separate. | The guide's combined Medicare-paid definition mixes financial scopes. |
| 2026-10-09 | Retain pre-2008 and undated costs with explicit window/enrollment flags. | Preserve $3,114,030 in 2007 medical payments and $392,320 in undated outpatient payments during reconciliation. |
| 2026-10-09 | Use latest annual member demographics and retain annual history separately. | A single member dimension cannot represent changing state/sex values without a stated convention. |
| 2026-10-09 | Include canonical inpatient attending NPIs in the observed provider dimension. | Avoid dangling nonblank provider references; do not infer real names or specialties. |
| 2026-10-09 | Validate every gold column description and configured index against the live database. | Ensure the documented interface and join/filter indexes actually exist. |
| 2026-10-09 | Index experiment: median 235.068 ms before, 27.686 ms after, identical results. | Three measured warm runs per condition on isolated, narrower full-row copies; this is a local selective-query result, not a universal production speedup. |
| 2026-10-09 | Run read-only reconciliation after dbt writes complete. | A concurrent seed refresh exposed an empty-seed snapshot; final stable-state audit passed 53 checks and 5,853,015 field comparisons. |
| 2026-10-09 | Defer dim_dx_ccs to Step 8 and capture only implemented lineage through gold. | Do not present future mappings or marts as already built. |
| 2026-10-09 | Publish verified Step 5 on step-05-gold with a draft PR based on step-04-silver. | The user explicitly approved this checkpoint push; earlier PRs remain unmerged and future pushes need separate approval. |
| 2026-10-09 | Separate blocking quality contracts from source-anomaly warnings. | Preserve negative adjustments, missing service dates, and conflicting headers while exposing counts for review. |
| 2026-10-09 | Screen event starts more than 30 days after the earliest observed member death date. | Verify the exact boundary with a fixture; monitor null service dates separately. |
| 2026-10-09 | Pin dbt-utils 1.4.1 and use SQLFluff's PostgreSQL/dbt templater. | Validate source-aware SQL with explicit lint rules and reproducible dependencies. |
| 2026-10-09 | Defer attribution and CCS-specific tests to their implementation checkpoints. | Do not report checks against nonexistent models as completed coverage. |
| 2026-10-09 | Accept Step 6 locally after the full build and independent audits. | 76 data tests and 6 unit tests passed, 3 source monitors warned, 34 regression tests passed, and all 199 reconciliation checks passed; push awaits approval. |
| 2026-10-10 | Continue the project and commit and push each verified checkpoint without further approval prompts. | The user explicitly replaced the earlier per-push approval workflow; retain verification and what/why/interview notes, and keep existing draft PRs unmerged. |

## Step 7 — reproducible retrospective attribution

Use eligible 2009/2010 member years, sample-aware keys, and an explicit NULL-NPI
row when unattributed. Method A counts distinct office E&M claim-from dates,
then latest office date and lowest NPI. Method B ranks known allowed sums across
all professional lines, then distinct service dates and lowest NPI. Unknown
allowed amounts never become paid amounts or known zeros: omit them from sums,
count them, and exclude candidates with no known amount. Preserve zero/negative
known amounts. This is a reproducible incomplete-amount policy, not imputation.
Candidates and winning tie counts remain auditable. All NPIs are text; no
specialty or identity assumptions. Panel ≥20 is a later reporting restriction,
not an attribution filter. Five deterministic spot checks are agent-verified,
explicitly not represented as user/human validation.

## Step 8 — conservative diagnosis grouping

Use the verified AHRQ 2015 single-level ICD-9 map as a fixed retrospective grouper.
Keep codes and categories as text. Do not map absent prefixes to an arbitrary
child code. Preserve unmapped diagnoses and report coverage by claim type;
error if any type exceeds 2% unmatched (observed maximum 0.274%). Assign inpatient
cost once through the canonical principal diagnosis, admission year and an
explicit UNMAPPED category. Any-position sensitivity uses distinct stay/category
pairs across all source segments and is nonadditive across categories. It changes
position policy, not grouper version. Reference absence alone does not establish
invalidity, truncation, or synthetic origin.

## Step 9 — auditable readmissions

Write the canonical readmission specification in assistant/measure_definitions.md
and link it from the financial/attribution definitions to avoid duplicate rules.
Merge overlaps and same-day transfers using the running maximum prior discharge;
retain all source IDs and payments. Retain invalid dated claims as excluded audit
rows and conservatively exclude their member's indices. Current/next header
conflicts exclude an index. Compute next admission before filtering; chained
readmissions can be indices. Use earliest member death, exclude death through the
full follow-up window, require the strict full-year annual FFS proxy in both years
when crossed, and allow December 1, 2010 (30 days available) but not December 2.
These are explicit project conventions, not CMS endorsement or verified continuous
enrollment. Retain subthreshold provider rows with a reporting flag for auditing.

## Step 10 — exposure and positive expected cost

Keep medical paid separate from Rx gross cost. Use annual required-month proxies
and independently aggregate admissions before joining panel costs; carry Step 9
discharge-year readmissions. Rank only panels >=20, with explicit NPI tie breaks.
Use exposure-weighted positive log-link quasi-likelihood rather than flooring
negative linear predictions or globally smearing log-cost predictions. Fixed
alpha=1; one negative training row excluded and counted, all observed values
preserved. Save coefficients and diagnostics in JSON, atomically refresh the
expected-cost table. Core dbt must precede Python risk fit and dependent mart.

## Step 11: consistent deciles and explicit comparison cohorts

Keep the operational mart's metric-then-NPI `NTILE(10)` policy for comparison
charts and high-cost groups; recompute it at each 10/20/30 panel threshold before
intersecting methods. This preserves dashboard consistency but can split ties.
Spearman instead uses average ranks of common-cohort raw scores. Top-decile
Jaccard is limited to that same common cohort; empty unions and fewer-than-ten
qualifying populations are unavailable. See [full policy](steps/11-comparison.md).
Coverage and reassignment have separate denominators. Export only provider-level
or aggregate results, including the mover's cohort/service decomposition.

## Step 11b: separate source evidence, atomic combined warehouse

Keep immutable historical Sample 1 evidence and a separate Sample 2 profile.
Default operational builds select both samples via `MEDICARE_SAMPLES=1,2`.
Combine source plans before any table truncation and reject incompatible headers
before opening the load transaction. Source identifiers require sample lineage;
provider comparisons retain their sample/year reference distributions. Refit the
2008 expected-cost model after the combined core build and regenerate findings
before interpreting the expanded dataset. Cached ZIPs must pass source identity,
hash, size, member safety and CRC checks before entering the normal manifest.
