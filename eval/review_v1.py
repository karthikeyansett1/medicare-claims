"""Deterministic checks supporting the agent's manually reviewed v1 failure labels.
Does not alter original scores or feed reference data into the assistant.
"""
import json
from pathlib import Path
from decimal import Decimal
import yaml
from assistant.database import execute
from eval.run_eval import compare_rows,TAXONOMY
ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'eval/results/v1_2026-10-14_resumed'
rows=[json.loads(x) for x in (run/'results.jsonl').read_text().splitlines()]
qs={q['id']:q for q in yaml.safe_load((ROOT/'eval/questions.yaml').read_text())['questions']}
selected={'Q06':[1],'Q11':[0,1],'Q14':[0,2],'Q33':[3],'Q40':[2],'Q41':[1,2,3],'Q44':[2],'Q45':[2]}
review=[]
for row in rows:
    if row['pass']: continue
    q=qs[row['id']]; gold=execute(q['gold_sql'])[1]; actual=execute(row['generated_sql'])[1]
    identifier=row['id']
    if identifier in selected:
        projection=[[list(r.values())[i] for i in selected[identifier]] for r in actual]
        equivalent=compare_rows(gold,projection,q.get('tolerance'),q.get('ordered',False))
        evidence='Requested values match after removing unrequested output columns; strict score remains failed.'
        subtype='extra_projection'
    elif identifier=='Q16':
        a=list(actual[0].values()); projection=[(True,a[0]),(False,a[1])]
        equivalent=compare_rows(gold,projection)
        evidence='Conditional-count pivot (130 meeting, 41239 below) equals grouped reference counts; shape differs, strict score remains failed.'
        subtype='equivalent_pivot_shape'
    elif identifier=='Q22':
        equivalent=False; evidence='Correct numerator/denominator, but extra counts and SQL ROUND(...,2) lose required numerical precision.'; subtype='early_rounding_and_projection'
    else:
        equivalent=False; evidence='Empty set returns COUNT=0 and SUM=NULL in reference; model COALESCE changes SUM to zero, erasing absent/unknown aggregate semantics.';subtype='empty_sum_null_to_zero'
    review.append({'id':identifier,'failure_type':TAXONOMY[9],'subtype':subtype,'failure_review':'reviewed_by_Codex_agent_not_human','failure_evidence':evidence,'requested_values_equivalent_under_explicit_manual_projection':equivalent,'gold_rows':gold,'generated_rows':actual})
report={'run':str(run.relative_to(ROOT)),'reviewer':'Codex agent (not human)','strict_score_unchanged':'39/50','failures':review,'taxonomy_counts':{label:sum(r['failure_type']==label for r in review) for label in TAXONOMY},'operational_attempts':[{'id':'Q20','original_run':'v1_2026-10-14','error':'APITimeoutError after 60 seconds','classification':'infrastructure, not accuracy failure','unknown_reservation_usd':'0.7631875','resumed_once_after_explicit_user_continue':True}]}
(run/'failure_review.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print('Failure review:',len(review),'manual equivalent:',sum(r['requested_values_equivalent_under_explicit_manual_projection'] for r in review))
