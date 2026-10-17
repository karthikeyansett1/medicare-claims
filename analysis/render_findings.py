"""Render current measured findings from verified comparison CSV exports."""
from pathlib import Path
import json
import pandas as pd


def main():
    root=Path(__file__).resolve().parents[1];out=root/'analysis/output'
    s=pd.read_csv(out/'method_comparison.csv');cov=pd.read_csv(out/'coverage.csv')
    base=s[(s.comparison=='A_vs_B_pmpm') & (s.min_panel==20)]
    if base.empty or base.duplicated(['_sample_id', 'year']).any():
        raise ValueError('Expected one PMPM comparison per sample/year')
    sample_label = ', '.join(str(int(x)) for x in sorted(base._sample_id.unique()))
    lines=['# Attribution sensitivity — measured findings','',
    f'Samples {sample_label}, performance years 2009 and 2010. All figures describe synthetic',
    'data. Each sample/year has its own ranking population. Provider identifiers are',
    'synthetic and do not establish real provider identity or specialty. The default',
    'panel threshold is 20 attributed eligible member-years.','',
    '## Coverage and reassignment','',
    'Coverage uses all eligible members; reassignment uses only members attributed',
    'under both methods. Method A uses office-visit plurality; Method B uses',
    'professional allowed amounts.','',
    '| Sample | Year | Eligible | Coverage A | Coverage B | Reassigned / jointly attributed |',
    '| --- | --- | ---: | ---: | ---: | ---: |']
    for _,r in cov.iterrows():
     lines.append(f"| {int(r._sample_id)} | {int(r.year)} | {int(r.eligible_members):,} | {r.coverage_a:.1%} | {r.coverage_b:.1%} | {int(r.reassigned):,} / {int(r.both_attributed):,} ({r.reassigned_fraction:.1%}) |")
    lines+=['','## Medical PMPM ranking sensitivity','','Deciles are calculated before intersecting the two qualifying provider cohorts.','Spearman uses common-cohort raw scores with average ranks for ties. High-cost','overlap is the common-cohort top-decile Jaccard. Operational deciles break ties','by synthetic NPI; these comparisons do not establish which method is better.','',
    '| Sample | Year | Common providers | Spearman | Moved ≥3 deciles | Top-decile Jaccard |',
    '| --- | --- | ---: | ---: | ---: | ---: |']
    for _,r in base.iterrows():
     lines.append(f"| {int(r._sample_id)} | {int(r.year)} | {int(r.common_providers)} | {r.spearman:.3f} | {int(r.movement_3)} ({r.movement_3/r.common_providers:.1%}) | {r.top_jaccard:.1%} |")
    lines+=['','At panel thresholds 10/20/30, the population and reference distribution both','change. These ranges are sensitivity analyses, not confidence intervals.','',
    '| Sample | Year | PMPM Spearman at 10 / 20 / 30 | Common providers at 10 / 20 / 30 |',
    '| --- | --- | --- | --- |']
    for (sample,year),g in s[s.comparison=='A_vs_B_pmpm'].groupby(['_sample_id','year']):
     g=g.sort_values('min_panel');lines.append(f"| {sample} | {year} | {' / '.join(f'{x:.3f}' for x in g.spearman)} | {' / '.join(str(x) for x in g.common_providers)} |")
    lines+=['','## Risk adjustment and readmissions','','The expected-cost model is refit on eligible 2008 records from the selected samples.','It is a concurrent descriptive GLM, not a clinically validated causal model.','Raw PMPM and O/E can rank the same providers differently. A 20-member panel','also does not guarantee a reliable readmission rate; index stays can be sparse.','',
    '| Sample | Year | Raw vs O/E Spearman A / B | A/B readmission Spearman | Readmission common providers |',
    '| --- | --- | ---: | ---: | ---: |']
    for (sample,year),g in s[s.min_panel==20].groupby(['_sample_id','year']):
     g=g.set_index('comparison');a=g.loc['A_raw_vs_oe'];b=g.loc['B_raw_vs_oe'];rd=g.loc['A_vs_B_readmission']
     lines.append(f"| {sample} | {year} | {a.spearman:.3f} / {b.spearman:.3f} | {rd.spearman:.3f} | {int(rd.common_providers)} |")
    diagnostics = json.loads((root/'analysis/risk_model_diagnostics.json').read_text())
    calibration = []
    for year in ('2009', '2010'):
        model = diagnostics['by_year'][year]['model']
        calibration.append(f"{year}: expected/observed paid {model['expected_paid']/model['observed_paid']:.3f}")
    lines += ['', 'Aggregate model calibration across the selected samples: ' + '; '.join(calibration) + '. This calibration limitation is another reason not to treat adjusted rankings as clinical quality.']
    w=pd.read_csv(out/'readmission_waterfall.csv')
    lines+=['',f"Across the selected samples and all audit years, ordered exclusions retain **{int(w.loc[w.stage=='eligible','episodes'].sum()):,} of {int(w.episodes.sum()):,} episodes**. The waterfall intentionally includes 2008 and out-of-window episodes.",'','## Why the largest global mover changed','']
    m=pd.read_csv(out/'greatest_mover.csv',dtype={'attributed_npi':str}).iloc[0]
    ref=base[(base._sample_id==m._sample_id)&(base.year==m.year)].iloc[0]
    lines += [f"Synthetic NPI **`{m.attributed_npi}`**, Sample **{int(m._sample_id)}**, **{int(m.year)}**, is the current largest absolute PMPM-decile mover across the selected samples. Ties use absolute rank movement, then sample/year/NPI. It moves from decile **{int(m.decile_left)} to {int(m.decile_right)}**, rank **{int(m.rank_left)}/{int(ref.left_providers)} to {int(m.rank_right)}/{int(ref.right_providers)}**, and PMPM **${m.value_left:,.2f} to ${m.value_right:,.2f}**.",'']
    c=pd.read_csv(out/'mover_cohorts.csv').set_index('cohort');a=c.loc['outgoing_A_only'];b=c.loc['incoming_B_only'];r=c.loc['retained']
    lines += [f"The A panel has **{int(a.members+r.members)} members** and B has **{int(b.members+r.members)}**: **{int(r.members)} retained**, **{int(a.members)} outgoing**, and **{int(b.members)} incoming**. Cohort replacement changes spending and exposure even when panel sizes look similar.",'',
    '| Cohort | Members | Member-months | Medical paid |','| --- | ---: | ---: | ---: |']
    for label,row in c.iterrows():lines.append(f'| {label} | {int(row.members)} | {int(row.member_months)} | ${row.medical_paid_amt:,.2f} |')
    lines+=['','| Medical paid component | Outgoing A-only | Incoming B-only | Incoming − outgoing |','| --- | ---: | ---: | ---: |']
    for label,col in [('Inpatient','inpatient_paid_amt'),('Outpatient','outpatient_paid_amt'),('Professional','professional_paid_amt'),('Total','medical_paid_amt')]:
     lines.append(f'| {label} | ${a[col]:,.2f} | ${b[col]:,.2f} | ${b[col]-a[col]:+,.2f} |')
    lines+=['','This is a cohort-composition explanation, not evidence of clinical cause or','services delivered by the attributed provider. Medical PMPM includes all','attributed members’ medical services regardless of rendering provider and','excludes Rx gross cost. The professional-service export reports HCPCS-level','paid and allowed amounts without member identifiers; those amounts are not','interchangeable. No diagnosis, specialty or clinical narrative is inferred.','',
    '## Inspect and reproduce','','Run `make compare verify-comparison` after `make pipeline-build`. See the',
    '[combined integration evidence](../docs/steps/11b-sample2.md) and',
    '[comparison policy](../docs/steps/11-comparison.md). Historical Sample 1 findings',
    'are retained in `docs/checkpoints/sample_1/analysis/`.','',
    '- [Aggregate comparisons](output/method_comparison.csv)',
    '- [Provider pairs](output/provider_comparison.csv)',
    '- [Mover cohorts](output/mover_cohorts.csv)',
    '- [Mover services](output/mover_services.csv)',
    '- [Independent verification](output/verification.json)','',
    '![PMPM rank comparison](output/pmpm_rank_scatter.png)',
    '![Absolute decile movements](output/decile_movement.png)',
    '![Ordered readmission exclusions](output/readmission_waterfall.png)','']
    (root/'analysis/findings.md').write_text('\n'.join(lines))


if __name__ == "__main__":
    main()
