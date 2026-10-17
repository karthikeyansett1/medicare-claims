"""Independent PostgreSQL window/corr reconciliation of exported comparisons."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ingest.db import get_conn
from analysis.compare_methods import query, OUT

COMPARISONS = {
    'A_vs_B_pmpm':('medical_pmpm','medical_pmpm','A_visits','B_allowed'),
    'A_vs_B_oe':('oe_ratio','oe_ratio','A_visits','B_allowed'),
    'A_vs_B_readmission':('readmission_rate','readmission_rate','A_visits','B_allowed'),
    'A_raw_vs_oe':('medical_pmpm','oe_ratio','A_visits','A_visits'),
    'B_raw_vs_oe':('medical_pmpm','oe_ratio','B_allowed','B_allowed'),
}


def live_comparison(conn, sample, year, threshold, name,
                    relation=('marts','mart_provider_performance')):
    """Independent SQL ranks, counts and correlations, including empty populations."""
    ml,mr,ma,mb=COMPARISONS[name]
    table=sql.Identifier(*relation).as_string(conn)
    def population(metric):
        # Strict bounds exclude PostgreSQL NaN as well as both infinities.
        return f"""select attributed_npi, {metric}::double precision as value
          from {table} where _sample_id=%s and year=%s and panel_size >= %s and method=%s
          and {metric}::double precision > '-Infinity'::double precision
          and {metric}::double precision < 'Infinity'::double precision
          and ('{metric}' <> 'readmission_rate' or index_stays>0)"""
    cte=f"with lp as ({population(ml)}), rp as ({population(mr)})"
    params=(sample,year,threshold,ma,sample,year,threshold,mb)
    counts=conn.execute(cte+' select (select count(*) from lp),(select count(*) from rp)',params).fetchone()
    statement=cte+""", l as (
      select attributed_npi,value as x,row_number() over(order by value,attributed_npi) rl,
        case when count(*) over()>=10 then ntile(10) over(order by value,attributed_npi) end dl
      from lp), r as (
      select attributed_npi,value as y,row_number() over(order by value,attributed_npi) rr,
        case when count(*) over()>=10 then ntile(10) over(order by value,attributed_npi) end dr
      from rp), pairs as (
      select *,rank() over(order by x)+(count(*) over(partition by x)-1)/2.0 ax,
        rank() over(order by y)+(count(*) over(partition by y)-1)/2.0 ay
      from l join r using(attributed_npi)
    ) select *,corr(ax,ay) over() rho from pairs order by attributed_npi"""
    return query(conn,statement,params), counts


def assert_comparison(live, counts, export, row):
    """Validate numeric values AND every unavailable-result status/null contract."""
    export=export.sort_values('attributed_npi')
    assert live.attributed_npi.tolist()==export.attributed_npi.tolist()
    for a,b in [('rl','rank_left'),('rr','rank_right'),('dl','decile_left'),('dr','decile_right')]:
        assert np.allclose(live[a].astype(float),export[b].astype(float),equal_nan=True),b
    assert counts==(row.left_providers,row.right_providers)
    assert len(live)==row.common_providers
    status=('too_few_common_providers' if len(live)<3 else
            'constant_input' if live.x.nunique()<2 or live.y.nunique()<2 else 'available')
    assert row.correlation_status==status
    if status=='available':
        assert np.isclose(float(live.rho.iloc[0]),row.spearman)
    else:
        assert pd.isna(row.spearman)
    left=set(live.loc[live.dl.eq(10),'attributed_npi'])
    right=set(live.loc[live.dr.eq(10),'attributed_npi'])
    assert len(left|right)==row.top_union and len(left&right)==row.top_intersection
    assert len(left)==row.top_left and len(right)==row.top_right
    deciles=all(n>=10 for n in counts)
    assert row.decile_status==('available' if deciles else 'too_few_qualifying_providers')
    expected=('too_few_qualifying_providers' if not deciles else
              'available' if left|right else 'empty_union')
    assert row.jaccard_status==expected
    if expected=='available':
        assert np.isclose(len(left&right)/len(left|right),row.top_jaccard)
    else:
        assert pd.isna(row.top_jaccard)
    movement=(live.dl.astype(float)-live.dr.astype(float)).abs()
    assert np.allclose(movement,export.decile_movement,equal_nan=True)
    assert np.allclose(movement.clip(upper=3),export.movement_bucket,equal_nan=True)
    for i in range(4):
        if deciles:
            assert int(movement.clip(upper=3).eq(i).sum())==getattr(row,f'movement_{i}')
        else:
            assert pd.isna(getattr(row,f'movement_{i}'))
    return len(live)*4+12


def assert_mart_consistency(detail, mart):
    """Only identical finite reference populations can share operational ranks.

    The mart also requires valid OE for raw ranks. Missing/nonfinite metric rows
    can legitimately make its original reference population differ from ours.
    """
    checks=0
    skipped=0
    for name,prefix,metric in [('A_vs_B_pmpm','raw','medical_pmpm'),('A_vs_B_oe','oe','oe_ratio')]:
        subset=detail.loc[(detail.comparison==name)&(detail.min_panel==20)]
        for side,method in [('left','A_visits'),('right','B_allowed')]:
            for (sample,year),population in mart.loc[mart.method==method].groupby(['_sample_id','year']):
                eligible=population.loc[np.isfinite(pd.to_numeric(population[metric]))]
                paired=subset.loc[(subset._sample_id==sample)&(subset.year==year)]
                ranked=population.loc[population[f'{prefix}_rank'].notna()]
                if set(eligible.attributed_npi)!=set(ranked.attributed_npi):
                    skipped+=1
                    continue
                merged=paired.merge(ranked,on=['_sample_id','year','attributed_npi'],validate='one_to_one')
                assert len(merged)==len(paired)
                assert np.allclose(merged[f'rank_{side}'],merged[f'{prefix}_rank'])
                checks+=len(merged)
                if len(eligible)>=10:
                    assert np.allclose(merged[f'decile_{side}'],merged[f'{prefix}_decile'])
                else:
                    assert merged[f'decile_{side}'].isna().all()
                checks+=len(merged)
    return checks,skipped


def verify(conn):
    summary=pd.read_csv(OUT/'method_comparison.csv')
    detail=pd.read_csv(OUT/'provider_comparison.csv',dtype={'attributed_npi':str})
    checked=0
    for row in summary.itertuples(index=False):
        sample,year,threshold,name=row[:4]
        live,counts=live_comparison(conn,sample,year,threshold,name)
        export=detail.loc[(detail._sample_id==sample)&(detail.year==year)&
                          (detail.min_panel==threshold)&(detail.comparison==name)]
        checked+=assert_comparison(live,counts,export,row)
    mart=query(conn,"""select _sample_id,year,attributed_npi,method,medical_pmpm,oe_ratio,
                      raw_rank,raw_decile,oe_rank,oe_decile
                      from marts.mart_provider_performance where meets_min_panel""")
    mart_checks,mart_skipped=assert_mart_consistency(detail,mart)
    coverage=query(conn,"""with members as (
      select _sample_id,year,member_year_key,
        max(attributed_npi) filter(where method='A_visits') a,
        max(attributed_npi) filter(where method='B_allowed') b
      from gold.attribution_long group by 1,2,3)
      select _sample_id,year,count(*) eligible_members,count(a) attributed_a,count(b) attributed_b,
        count(*) filter(where a is not null and b is not null) both_attributed,
        count(*) filter(where a<>b) reassigned
      from members group by 1,2 order by 1,2""")
    saved=pd.read_csv(OUT/'coverage.csv')
    pd.testing.assert_frame_equal(coverage,saved[coverage.columns],check_dtype=False)
    persisted=query(conn,'select * from analysis.method_comparison order by _sample_id,year,min_panel,comparison')
    pd.testing.assert_frame_equal(persisted,summary.sort_values(['_sample_id','year','min_panel','comparison']).reset_index(drop=True),check_dtype=False,rtol=1e-10)
    # Independently reconstruct traced A/B panels from cohort aggregates, then reconcile marts.
    mover=pd.read_csv(OUT/'greatest_mover.csv',dtype={'attributed_npi':str}).iloc[0]
    cohorts=pd.read_csv(OUT/'mover_cohorts.csv').set_index('cohort')
    totals=query(conn,"""select method,panel_size,member_months,medical_paid_amt,medical_pmpm
       from marts.mart_provider_performance where _sample_id=%s and year=%s and attributed_npi=%s""",
       (int(mover._sample_id),int(mover.year),mover.attributed_npi)).set_index('method')
    for method,cohort in [('A_visits','outgoing_A_only'),('B_allowed','incoming_B_only')]:
        c=cohorts.loc[['retained',cohort]].sum()
        t=totals.loc[method]
        assert c.members==t.panel_size and c.member_months==t.member_months
        assert np.isclose(c.medical_paid_amt,float(t.medical_paid_amt))
        assert np.isclose(c.medical_paid_amt/c.member_months,float(t.medical_pmpm))
    services=pd.read_csv(OUT/'mover_services.csv')
    for cohort,group in services.groupby('cohort'):
        assert np.isclose(group.professional_paid_amt.sum(),cohorts.loc[cohort,'professional_paid_amt'])
    waterfall=pd.read_csv(OUT/'readmission_waterfall.csv')
    assert int(waterfall.episodes.sum())==conn.execute('select count(*) from gold.fct_readmissions').fetchone()[0]
    result=dict(status='PASS',comparisons=len(summary),provider_pairs=len(detail),
                independent_sql_numeric_checks=checked,mart_rank_decile_checks=mart_checks,
                mart_populations_skipped_different_eligibility=mart_skipped,
                coverage_groups=len(coverage),persisted_rows=len(persisted),mover_panels_reconciled=2,
                mover_service_cohorts_reconciled=len(cohorts),waterfall_episodes=int(waterfall.episodes.sum()))
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    with get_conn() as conn:
        print(json.dumps(verify(conn),indent=2))
