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
