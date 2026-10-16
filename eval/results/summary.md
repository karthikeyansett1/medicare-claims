# Real API evaluation results

The complete fixed 50-question v1 baseline scored **39/50 (78%)**. After three general prompt improvements, v2 scored **49/50, 49/50, and 49/50**. The observed v2 accuracy range is **98%–98%** (population standard deviation 0.00 percentage points). These are real Responses API runs using `gpt-6-astra`, standard tier, low reasoning, and a 3,000-output-token cap. Temperature was omitted; these are not temperature-zero trials.

## What the scores measure

Each run has 45 executable SQL questions and five expected clarifications. SQL execution succeeded on all 45 non-ambiguous cases per completed run, and all five clarification cases passed. The strict comparator ignores column labels but preserves column position, shape, types, duplicates, ordering when requested, and declared numeric tolerance. Strict result agreement is distinct from whether SQL executes or an answer is faithful.

The smoke completed all eight public examples: 7/8 strict matches. The remaining answer had correct requested values plus an extra diagnostic column. Smoke questions are training examples, not held-out evidence.

## Failure review and prompt changes

The v1 eleven strict failures all receive exactly one reviewed taxonomy label: **Other (describe)**. Eight add unrequested columns; one returns equivalent pivoted counts; one adds columns and rounds a percentage too early; one changes an empty SUM from NULL to zero. Nine preserve the requested values under explicitly reviewed projection/pivot mappings. The reported 39/50 score is unchanged.

Three actual examples illustrate the issues:

- **Q06:** the requested earliest service date is correct, but an extra fixed-NPI column changes the result shape.
- **Q22:** the correct attribution fraction is rounded in SQL to 86.45 and accompanied by extra count columns, losing the required precision/shape.
- **Q29:** an empty group should yield count 0 and sum NULL; `COALESCE(SUM(...),0)` reports zero instead of an absent aggregate.

V2 adds only general rules: return requested measures and grouping dimensions, preserve SQL precision unless rounding is requested, and preserve empty/missing SUM as NULL unless the definition calls for zero. Gold SQL, question text, expected values, comparator, schema, definitions, and few-shots were not inserted into or changed for the model prompt. The Q16 pivot representation was not forced to match the reference.

V2 remaining failures: 3 instances of Q16, all equivalent pivot shape under **Other (describe)**; all other nine taxonomy buckets have zero reviewed failures. See the per-run failure-review JSON for evidence. This is a fixed-set regression after inspecting v1 failures; it is **not an untouched held-out generalization estimate**.

## Answer faithfulness

The 15 question IDs were selected before paid outputs existed. Manual **Codex agent** inspection scored v1 **15/15** and v2 repetition 1 **15/15**, checking stated scope, method, year, measure definitions and numerical claims against SQL/results. These are agent reviews, **not human reviews**; human review remains pending. Literal answer excerpts and case-by-case evidence are preserved in each completed run's `faithfulness_review.json`.

## Spend and interruption accounting

Measured usage-based cost is **$6.5081800**. Two historical timeout calls have unknown usage; their full reservations total **$1.0315875**. Thus **$7.5397675** is charged or reserved against the **$20 hard cap**, including both smoke stages and all evaluation attempts. Unknown spend is not zero. This is not an invoice, live account balance, or account-wide spend total.

V1 Q20 timed out during planning; v2 repetition 2 Q23 timed out during explanation after successful SQL. Each received one fresh attempt after explicit user continuation. Original incomplete runs remain immutable and carry no aggregate accuracy claim. Completed lineage-linked runs reuse already answered cases without resending them. The original Q23 token fields contain only known planning usage; supplemental lineage/failure review correctly marks total question usage unknown.

Reservations occur before API dispatch and settle only after valid, bounded usage with verified model/tier and cache accounting. Unknown reservations are never released. Existing six-calls-per-minute pacing was retained; larger daily limits apply only inside the explicitly authorized offline owner process. Public live AI remains disabled.

## Evidence

- [Complete v1](v1_2026-10-14_resumed/summary.json), [reviewed failures](v1_2026-10-14_resumed/failure_review.json), [faithfulness](v1_2026-10-14_resumed/faithfulness_review.json)
- [Complete v2](v2_2026-10-16_resumed/summary.json), [reviewed failures](v2_2026-10-16_resumed/failure_review.json), [faithfulness](v2_2026-10-16_resumed/faithfulness_review.json)
- [Full machine-readable comparison](final_evaluation_summary.json), [sanitized cost evidence](cost_evidence_2026-10-15.json)
- Immutable prompt snapshots and SHA-256 manifests are inside each run. The original interrupted directories and lineage files remain available.

Pricing used: [official Astra model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra), verified October 14, 2026: $10/M uncached input, $1/M cache reads, $12.50/M cache writes, $50/M output including reasoning. Cache writes are counted separately, not double charged.
