"""Reproducible provider-level sensitivity exports; see docs/steps/11-comparison.md."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', '/tmp/medicare-matplotlib')
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from ingest.db import get_conn

OUT = ROOT / 'analysis/output'


def query(conn, sql, params=None):
    cur = conn.execute(sql, params)
    return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


def ranked(frame, metric, threshold):
    """Match SQL row_number/ntile(10), ordered by value then synthetic NPI."""
    qualifies = frame.panel_size.ge(threshold)
    if metric == 'readmission_rate':
        qualifies &= pd.to_numeric(frame.index_stays).fillna(0).gt(0)
    f = frame.loc[qualifies, ['attributed_npi', metric]].copy()
    f['value'] = pd.to_numeric(f.pop(metric), errors='raise')
    f = f.loc[np.isfinite(f.value)].copy()
    f = f.sort_values(['value', 'attributed_npi'])
    f['rank'] = np.arange(1, len(f) + 1)
    # PostgreSQL puts the remainder into the first buckets. Small populations
    # have fewer than ten groups: retain ranks but mark deciles unavailable.
    q, remainder = divmod(len(f), 10)
    f['decile'] = (np.repeat(np.arange(1, 11), [q + (i < remainder) for i in range(10)])
                   if len(f) >= 10 else np.full(len(f), np.nan))
    return f.set_index('attributed_npi')


def compare(left, right, metric_left, metric_right, threshold):
    a, b = ranked(left, metric_left, threshold), ranked(right, metric_right, threshold)
    pair = a.join(b, how='inner', lsuffix='_left', rsuffix='_right')
    pair['decile_movement'] = (pair.decile_left - pair.decile_right).abs()
    pair['movement_bucket'] = pair.decile_movement.clip(upper=3)
    n = len(pair)
    reason = 'too_few_common_providers' if n < 3 else (
        'constant_input' if pair.value_left.nunique() < 2 or pair.value_right.nunique() < 2 else 'available')
    rho = float(spearmanr(pair.value_left, pair.value_right).statistic) if reason == 'available' else None
    # Define high-cost sets only inside the common cohort, using independently computed deciles.
    top_a = set(pair.index[pair.decile_left.eq(10)])
    top_b = set(pair.index[pair.decile_right.eq(10)])
    union = len(top_a | top_b)
    deciles_available = len(a) >= 10 and len(b) >= 10
    result = dict(left_providers=len(a), right_providers=len(b), common_providers=n,
                  spearman=rho, correlation_status=reason, top_left=len(top_a), top_right=len(top_b),
                  top_intersection=len(top_a & top_b), top_union=union,
                  top_jaccard=len(top_a & top_b) / union if union and deciles_available else None,
                  jaccard_status=('too_few_qualifying_providers' if not deciles_available else
                                  'available' if union else 'empty_union'),
                  decile_status='available' if deciles_available else 'too_few_qualifying_providers')
    result.update({f'movement_{i}': int(pair.movement_bucket.eq(i).sum()) if deciles_available else None for i in range(4)})
    return result, pair.reset_index()


COVERAGE_SQL = """
select y._sample_id, y.year, count(*) as eligible_members,
 count(a.attributed_npi) as attributed_a, count(b.attributed_npi) as attributed_b,
 count(*) filter(where a.attributed_npi is not null and b.attributed_npi is not null) as both_attributed,
 count(*) filter(where a.attributed_npi is not null and b.attributed_npi is not null
 and a.attributed_npi <> b.attributed_npi) as reassigned
from gold.dim_member_year y
left join gold.attribution_a a using(member_year_key)
left join gold.attribution_b b using(member_year_key)
where y.is_ffs_eligible and y.year in (2009,2010)
group by y._sample_id, y.year order by 1,2
"""


def run(conn):
    providers = query(conn, 'select * from marts.mart_provider_performance order by _sample_id,year,method,attributed_npi')
    coverage = query(conn, COVERAGE_SQL)
    coverage['coverage_a'] = coverage.attributed_a / coverage.eligible_members
    coverage['coverage_b'] = coverage.attributed_b / coverage.eligible_members
    coverage['reassigned_fraction'] = coverage.reassigned / coverage.both_attributed.replace(0, np.nan)
    summaries, pairs = [], []
    for (sample, year), group in providers.groupby(['_sample_id', 'year'], sort=True):
        a = group.loc[group.method.eq('A_visits')]
        b = group.loc[group.method.eq('B_allowed')]
        for threshold in (10, 20, 30):
            for name, left, right, ml, mr in (
                ('A_vs_B_pmpm', a, b, 'medical_pmpm', 'medical_pmpm'),
                ('A_vs_B_oe', a, b, 'oe_ratio', 'oe_ratio'),
                ('A_vs_B_readmission', a, b, 'readmission_rate', 'readmission_rate'),
                ('A_raw_vs_oe', a, a, 'medical_pmpm', 'oe_ratio'),
                ('B_raw_vs_oe', b, b, 'medical_pmpm', 'oe_ratio'),
            ):
                metadata = dict(_sample_id=sample, year=year, min_panel=threshold, comparison=name)
                result, detail = compare(left, right, ml, mr, threshold)
                summaries.append(metadata | result)
                pairs.append(detail.assign(**metadata))
    summary = pd.DataFrame(summaries).merge(coverage, on=['_sample_id','year'], validate='many_to_one')
    detail = pd.concat(pairs, ignore_index=True)
    waterfall = query(conn, """select _sample_id, coalesce(exclusion_reason,'eligible') as stage,
        count(*) as episodes from gold.fct_readmissions group by 1,2 order by 1,2""")
    OUT.mkdir(exist_ok=True)
    for name, f in [('method_comparison',summary), ('provider_comparison',detail),
                    ('coverage',coverage), ('readmission_waterfall',waterfall)]:
        f.to_csv(OUT / f'{name}.csv', index=False, float_format='%.12g')
    publish(conn, summary)
    trace(conn, detail)
    charts(detail, waterfall)
    return summary


def publish(conn, frame):
    """Atomic replacement of an aggregate-only table; inferred types are explicit SQL types."""
    from psycopg import sql
    columns = []
    for col, dtype in frame.dtypes.items():
        typ = 'bigint' if pd.api.types.is_integer_dtype(dtype) else (
            'double precision' if pd.api.types.is_numeric_dtype(dtype) else 'text')
        columns.append(sql.SQL('{} {}').format(sql.Identifier(col), sql.SQL(typ)))
    conn.execute('create schema if not exists analysis')
    conn.execute('drop table if exists analysis.method_comparison')
    conn.execute(sql.SQL('create table analysis.method_comparison ({}, primary key (_sample_id,year,min_panel,comparison))').format(sql.SQL(',').join(columns)))
    with conn.cursor().copy('copy analysis.method_comparison from stdin') as copy:
        for row in frame.itertuples(index=False, name=None):
            copy.write_row(tuple(None if pd.isna(v) else v for v in row))


def trace(conn, detail):
    candidates = detail.loc[detail.comparison.eq('A_vs_B_pmpm') & detail.min_panel.eq(20)].copy()
    candidates['rank_movement'] = (candidates.rank_left - candidates.rank_right).abs()
    mover = candidates.sort_values(['decile_movement','rank_movement','_sample_id','year','attributed_npi'],
                                  ascending=[False,False,True,True,True]).head(1)
    if mover.empty:
        raise ValueError('No common providers at threshold 20 to trace')
    row = mover.iloc[0]
    params = (int(row._sample_id), int(row.year), str(row.attributed_npi), str(row.attributed_npi))
    cte = """with members as (
      select a.member_year_key,a.member_key,a.year,
        case when a.attributed_npi=b.attributed_npi then 'retained'
             when a.attributed_npi=%s then 'outgoing_A_only' else 'incoming_B_only' end as cohort
      from gold.attribution_a a join gold.attribution_b b using(member_year_key)
      where a._sample_id=%s and a.year=%s and (a.attributed_npi=%s or b.attributed_npi=%s)
    ) """
    args = (str(row.attributed_npi), *params)
    totals = query(conn, cte + """select cohort,count(*) as members,sum(y.required_months) as member_months,
       sum(c.inpatient_paid_amt) as inpatient_paid_amt,sum(c.outpatient_paid_amt) as outpatient_paid_amt,
       sum(c.professional_paid_amt) as professional_paid_amt,sum(c.medical_paid_amt) as medical_paid_amt
       from members m join gold.fct_member_year_cost c using(member_year_key)
       join gold.dim_member_year y using(member_year_key) group by cohort order by cohort""", args)
    services = query(conn, cte + """select cohort,coalesce(p.hcpcs_cd,'MISSING') as hcpcs_cd,
       count(*) as lines,count(distinct m.member_year_key) as members,
       sum(p.paid_amt) as professional_paid_amt,sum(p.allowed_amt) as professional_allowed_amt
       from members m join gold.fct_professional_lines p on m.member_key=p.member_key
        and extract(year from p.service_dt)=m.year
       group by 1,2 order by 1,professional_paid_amt desc nulls last,2""", args)
    for name,f in [('greatest_mover',mover),('mover_cohorts',totals),('mover_services',services)]:
        f.to_csv(OUT / f'{name}.csv',index=False,float_format='%.12g')


def charts(detail, waterfall):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    base = detail.loc[detail.comparison.eq('A_vs_B_pmpm') & detail.min_panel.eq(20)]
    groups = list(base.groupby(['_sample_id','year']))
    fig, axes = plt.subplots(1,len(groups),figsize=(6*len(groups),5),squeeze=False)
    for ax, ((sample, year), data) in zip(axes.flat, groups):
        ax.scatter(data.rank_left,data.rank_right,s=28,alpha=.65,color='#136f91')
        high = max(data.rank_left.max(),data.rank_right.max())
        ax.plot([0,high],[0,high],color='#ca6b35',linestyle='--')
        ax.set(xlabel='Method A PMPM rank',ylabel='Method B PMPM rank',
               title=f'Sample {sample} · {year} · {len(data)} common providers',xlim=(0,high+2),ylim=(0,high+2))
        ax.set_aspect('equal')
    fig.suptitle('Synthetic provider ranks · panel ≥20 in both methods · higher = higher cost')
    fig.tight_layout(); fig.savefig(OUT/'pmpm_rank_scatter.png',dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1,len(groups),figsize=(6*len(groups),4.7),squeeze=False)
    for ax, ((sample,year), data) in zip(axes.flat,groups):
        counts = data.movement_bucket.value_counts().reindex(range(4),fill_value=0)
        bars = ax.bar(['0','1','2','3+'],counts,color='#136f91')
        ax.bar_label(bars,padding=3)
        ax.set(xlabel='Absolute decile movement',ylabel='Common providers',title=f'Sample {sample} · {year}')
        ax.set_ylim(0,max(counts)*1.18)
    fig.suptitle('Synthetic PMPM decile movement · panel ≥20 · deciles before cohort intersection')
    fig.tight_layout();fig.savefig(OUT/'decile_movement.png',dpi=160);plt.close(fig)
    stages = waterfall.groupby('stage',sort=True).episodes.sum()
    excluded = stages.drop('eligible',errors='ignore')
    labels = ['All episodes'] + [s.split('_',1)[1].replace('_',' ') for s in excluded.index] + ['Eligible']
    heights = [int(stages.sum())]+excluded.tolist()+[int(stages.get('eligible',0))]
    remaining = int(stages.sum()); bottoms=[0]
    for value in excluded:
        remaining -= value; bottoms.append(remaining)
    bottoms.append(0)
    fig,ax = plt.subplots(figsize=(12,6))
    bars=ax.bar(range(len(labels)),heights,bottom=bottoms,color=['#136f91']+['#ca6b35']*len(excluded)+['#34845d'])
    for bar,value in zip(bars,heights):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_y()+bar.get_height()+800,f'{value:,}',ha='center',fontsize=8)
    ax.set_xticks(range(len(labels)),labels,rotation=32,ha='right')
    ax.set(ylabel='Episodes',title='Synthetic readmission exclusions · all audit years · ordered first exclusion')
    ax.set_ylim(0,stages.sum()*1.13)
    fig.tight_layout();fig.savefig(OUT/'readmission_waterfall.png',dpi=160);plt.close(fig)


if __name__ == '__main__':
    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read')
        result=run(conn)
    print(f'Published {len(result)} aggregate comparisons and provider-level exports to {OUT}')
