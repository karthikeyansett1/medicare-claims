"""Assemble completed evidence without changing raw generations or original scores."""
import json
from pathlib import Path
from statistics import mean,pstdev
from eval.run_eval import TAXONOMY
from eval.export_cost_evidence import main as export_cost
ROOT=Path(__file__).resolve().parents[1]


def main():
    v1=ROOT/'eval/results/v1_2026-10-14_resumed'
    v2=ROOT/'eval/results/v2_2026-10-16_resumed'
    a=[json.loads(x) for x in (v1/'results.jsonl').read_text().splitlines()]
    b=[json.loads(x) for x in (v2/'results.jsonl').read_text().splitlines()]
    if len(a)!=50 or len(b)!=150 or any(r['error'] for r in a+b):
        raise SystemExit('Final evidence requires complete runs without unresolved infrastructure errors.')
    failures=[]
    for r in b:
        if r['pass']:continue
        if r['id']!='Q16':raise SystemExit('New v2 failure requires manual review: '+r['id'])
        values=list(r['result_rows'][0].values())
        if values != [130,41239]:raise SystemExit('Unexpected Q16 values require review')
        failures.append({'id':r['id'],'repetition':r['repetition'],'failure_type':TAXONOMY[9],
                         'subtype':'equivalent_pivot_shape','failure_review':'reviewed_by_Codex_agent_not_human',
                         'failure_evidence':'Both counts match (130 meeting minimum panel; 41239 below); one pivoted row differs from grouped reference rows. Strict failure retained.',
                         'requested_values_equivalent_under_explicit_manual_projection':True})
    counts={label:sum(r['failure_type']==label for r in failures) for label in TAXONOMY}
    (v2/'failure_review.json').write_text(json.dumps({'reviewer':'Codex agent, not human','failures':failures,'taxonomy_counts':counts,'operational_attempts':[{'run':'v2_2026-10-15','repetition':2,'id':'Q23','error':'APITimeoutError during explanation after successful SQL','total_input_tokens':None,'total_output_tokens':None,'known_planning_tokens':{'input':8567,'output':127},'unknown_reserved_usd':'0.2684','continued_once_after_explicit_user_request':True}]},indent=2)+'\n')
    scores=[sum(r['pass'] for r in b if r['repetition']==i) for i in (1,2,3)]
    export_cost();cost=json.loads((ROOT/'eval/results/cost_evidence_2026-10-15.json').read_text())
    summary={'kind':'real_api_fixed_set_regression_evaluation','v1':{'strict_passes':sum(r['pass'] for r in a),'total':50,'sql_executed':sum(r['sql_executed'] for r in a),'clarifications_correct':sum(r['pass'] and r['category']=='ambiguous' for r in a)},'v2':{'strict_passes_by_repetition':scores,'total_per_repetition':50,'accuracy_range':[min(scores)/50,max(scores)/50],'accuracy_mean':mean(scores)/50,'accuracy_population_stddev':pstdev(scores)/50,'sql_executed_by_repetition':[sum(r['sql_executed'] for r in b if r['repetition']==i) for i in (1,2,3)],'clarifications_correct_by_repetition':[sum(r['pass'] and r['category']=='ambiguous' for r in b if r['repetition']==i) for i in (1,2,3)]},'faithfulness':{'v1':'15/15','v2_repetition_1':'15/15','reviewer':'Codex agent; human review pending'},'cost':cost,'limitations':['Strict positional comparator rejects equivalent output shapes; reported scores are unchanged.','v2 reuses the fixed 50-question set after v1-guided general prompt revisions; this is regression evidence, not untouched-test generalization.','Two timeouts were resumed once each after explicit user continuation; unknown costs retained and original partial runs preserved.','Usage-based cost estimate is not a provider invoice or remaining account balance.','Standard tier, low reasoning, max output 3000; temperature omitted, not temperature zero.']}
    (ROOT/'eval/results/final_evaluation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    text=f'''# Real API evaluation results

The complete fixed 50-question v1 baseline scored **39/50 (78%)**. After three general prompt improvements, v2 scored **{scores[0]}/50, {scores[1]}/50, and {scores[2]}/50**. The observed v2 accuracy range is **{min(scores)*2}%–{max(scores)*2}%** (population standard deviation {pstdev(scores)*2:.2f} percentage points). These are real Responses API runs using `gpt-6-astra`, standard tier, low reasoning, and a 3,000-output-token cap. Temperature was omitted; these are not temperature-zero trials.

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

V2 remaining failures: {len(failures)} instances of Q16, all equivalent pivot shape under **Other (describe)**; all other nine taxonomy buckets have zero reviewed failures. See the per-run failure-review JSON for evidence. This is a fixed-set regression after inspecting v1 failures; it is **not an untouched held-out generalization estimate**.

## Answer faithfulness

The 15 question IDs were selected before paid outputs existed. Manual **Codex agent** inspection scored v1 **15/15** and v2 repetition 1 **15/15**, checking stated scope, method, year, measure definitions and numerical claims against SQL/results. These are agent reviews, **not human reviews**; human review remains pending. Literal answer excerpts and case-by-case evidence are preserved in each completed run's `faithfulness_review.json`.

## Spend and interruption accounting

Measured usage-based cost is **${cost['known_usage_cost_usd']}**. Two historical timeout calls have unknown usage; their full reservations total **${cost['unknown_reserved_usd']}**. Thus **${cost['charged_or_reserved_usd']}** is charged or reserved against the **$20 hard cap**, including both smoke stages and all evaluation attempts. Unknown spend is not zero. This is not an invoice, live account balance, or account-wide spend total.

V1 Q20 timed out during planning; v2 repetition 2 Q23 timed out during explanation after successful SQL. Each received one fresh attempt after explicit user continuation. Original incomplete runs remain immutable and carry no aggregate accuracy claim. Completed lineage-linked runs reuse already answered cases without resending them. The original Q23 token fields contain only known planning usage; supplemental lineage/failure review correctly marks total question usage unknown.

Reservations occur before API dispatch and settle only after valid, bounded usage with verified model/tier and cache accounting. Unknown reservations are never released. Existing six-calls-per-minute pacing was retained; larger daily limits apply only inside the explicitly authorized offline owner process. Public live AI remains disabled.

## Evidence

- [Complete v1](v1_2026-10-14_resumed/summary.json), [reviewed failures](v1_2026-10-14_resumed/failure_review.json), [faithfulness](v1_2026-10-14_resumed/faithfulness_review.json)
- [Complete v2](v2_2026-10-16_resumed/summary.json), [reviewed failures](v2_2026-10-16_resumed/failure_review.json), [faithfulness](v2_2026-10-16_resumed/faithfulness_review.json)
- [Full machine-readable comparison](final_evaluation_summary.json), [sanitized cost evidence](cost_evidence_2026-10-15.json)
- Immutable prompt snapshots and SHA-256 manifests are inside each run. The original interrupted directories and lineage files remain available.

Pricing used: [official Astra model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra), verified October 14, 2026: $10/M uncached input, $1/M cache reads, $12.50/M cache writes, $50/M output including reasoning. Cache writes are counted separately, not double charged.
'''
    (ROOT/'eval/results/summary.md').write_text(text)
    (ROOT/'eval/results/faithfulness_review.md').write_text('''# Answer faithfulness review

The 15 preselected IDs are Q01, Q04, Q09, Q12, Q17, Q20, Q25, Q28, Q31, Q34, Q35, Q38, Q41, Q43 and Q45.

Manual **Codex agent** review: **v1 15/15; v2 repetition 1 15/15**. Human review remains pending. Each case was inspected against generated SQL, executed rows, stated method/year/scope/definitions, and numerical claims; formatting-only strict failures do not automatically imply unfaithful prose.

Full excerpts, evidence, reviewer provenance and run hashes: [v1 review](v1_2026-10-14_resumed/faithfulness_review.json) and [v2 review](v2_2026-10-16_resumed/faithfulness_review.json). These are small, purposive reviews, not independent human scoring or broad population estimates.
''')
    print('Final strict scores:',39,scores)

if __name__=='__main__':main()
