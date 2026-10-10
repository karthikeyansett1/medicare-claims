# Step 8 — AHRQ CCS diagnosis grouping

## What we are doing

Clean the original public 2015 single-level ICD-9-CM CCS map into a deterministic,
text-typed seed, then join it to every diagnosis without dropping unmatched rows.
The cleaner finds the quoted header after the note, trims padding and quotes,
excludes the blank-code placeholder, and rejects conflicting duplicate mappings.
Leading zeros and V/E prefixes survive. Spaces, case and decimal punctuation are
normalized consistently; missing digits are never guessed.

Build a cost mart using each inpatient stay's canonical principal diagnosis and
admission year. Keep an explicit UNMAPPED bucket. Each stay and its entire payment
lands in exactly one category; negative payments remain adjustments. Member counts
are distinct sample-aware member keys within each category/year and are not
additive across categories or years.

## Why

Diagnosis groupers turn thousands of codes into interpretable clinical categories.
The mapping must not duplicate facts, erase unknown diagnoses, or inflate payments.
Using all diagnoses changes category membership: secondary conditions may be common
and expensive even when they are not the principal reason for admission. That
comparison is useful, but its category payments cannot be summed as unique spending.
The fixed 2015 mapping is a retrospective grouping of 2008–2010 synthetic claims;
unmatched historical codes do not automatically mean invalid or synthetic junk.

## Verification and evidence

Run `make grouper`, `make verify-grouper`, and
`.venv/bin/python -m pytest tests/test_clean_ccs.py -q`.
The targeted dbt build passed 8 data tests and 2 unit fixtures, building one seed
and three models. Three cleaner tests and SQL lint for all three models passed.
The build verifies normalization, unknown-code preservation,
negative adjustments, sample-aware member counts and principal cost conservation.
Python independently reconstructs all category/year aggregates from the inpatient
facts and original reference file, and recomputes diagnosis coverage from the
ungrouped source codes. See [coverage and unmatched-code evidence](../ccs_verification.md)
and [principal versus any-position top ten](../../analysis/ccs_sensitivity.md).

Any-position assignments use distinct stay/category pairs across all source
segments. This prevents repeated positions in one category from duplicating a stay
within that category, but deliberately allows a stay in multiple categories.
The top-ten comparison changes diagnosis-position policy, not the CCS release.

## How to explain it in an interview

“I made a reproducible ICD-9-to-CCS mapping and measured what it could not classify.
I reconciled every inpatient dollar using one principal category per stay, keeping
unknowns visible. Then I compared principal and any-diagnosis rankings to show how
methodology changes condition-level results. I explicitly labeled the latter as
nonadditive so no one mistakes overlapping condition costs for total spending.”

## Publication and source evidence

Published in [draft PR #8](https://github.com/karthikeyansett1/medicare-claims/pull/8)
from `codex/step-08-grouper` under the standing authorization to commit
and push each verified checkpoint. Earlier draft PRs remain unmerged. The final
manifest matches `mart_cost_by_ccs` exactly; `dim_dx_ccs` and
`silver_diagnoses_grouped` differ only in SQL whitespace after formatting.
The build evidence records current source hashes and these formatting differences.
