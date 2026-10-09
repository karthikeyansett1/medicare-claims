"""Measure an indexed join on isolated full-size copies, without dropping gold indexes."""
import json
import statistics
import time
import uuid
from datetime import datetime, timezone

from psycopg import sql

from ingest.db import ROOT, get_conn


def main():
    started = time.monotonic()
    schema = 'bench_gold_' + uuid.uuid4().hex[:12]
    result = {}
    with get_conn() as conn:
        try:
            conn.execute(sql.SQL('create schema {}').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('create table {}.lines as select member_key,rendering_npi,service_dt,paid_amt from gold.fct_professional_lines').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('create table {}.members as select member_key,sex_cd from gold.dim_member').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('analyze {}.lines').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('analyze {}.members').format(sql.Identifier(schema)))
            conn.commit()
            npi=conn.execute('select npi from gold.dim_provider order by total_lines_billed desc,npi limit 1').fetchone()[0]
            query=sql.SQL('''select m.sex_cd,count(*) as line_count,sum(p.paid_amt) as paid_amt
              from {}.lines p join {}.members m using(member_key)
              where p.rendering_npi=%s and p.service_dt >= date '2008-01-01'
                and p.service_dt < date '2009-01-01'
              group by m.sex_cd order by m.sex_cd nulls last''').format(sql.Identifier(schema),sql.Identifier(schema))
            params=(npi,)
            settings={name:conn.execute(sql.SQL('show {}').format(sql.Identifier(name))).fetchone()[0]
                      for name in ['work_mem','max_parallel_workers_per_gather','shared_buffers']}
            def trial():
                return conn.execute(sql.SQL('explain (analyze,buffers,format json) ')+query,params).fetchone()[0][0]
            # One warm-up and three measured runs on each side. Do not force scan types.
            trial()
            before=[trial() for _ in range(3)]
            before_rows=conn.execute(query,params).fetchall()
            print('Baseline measurements complete.',flush=True)
            conn.execute(sql.SQL('create index lines_provider_date on {}.lines (rendering_npi,service_dt)').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('create unique index members_key on {}.members (member_key)').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('analyze {}.lines').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('analyze {}.members').format(sql.Identifier(schema)))
            conn.commit()
            trial()
            after=[trial() for _ in range(3)]
            after_rows=conn.execute(query,params).fetchall()
            if before_rows != after_rows:raise RuntimeError('Indexed query changed the result.')
            b=statistics.median(p['Execution Time'] for p in before)
            a=statistics.median(p['Execution Time'] for p in after)
            result=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),
                        scope='Isolated full-size copies of professional fact join columns and member dimension; not a cold-cache or production benchmark.',
                        query='Professional lines for the most frequently observed rendering NPI in calendar 2008, joined to members and grouped by sex.',
                        selection='Highest total_lines_billed, with NPI as deterministic tie-breaker.',
                        protocol='One warm-up plus three measured EXPLAIN ANALYZE BUFFERS runs before and after indexes; planner settings unchanged.',
                        copied_line_rows=conn.execute(sql.SQL('select count(*) from {}.lines').format(sql.Identifier(schema))).fetchone()[0],
                        copied_member_rows=conn.execute(sql.SQL('select count(*) from {}.members').format(sql.Identifier(schema))).fetchone()[0],
                        settings=settings,before_ms=[p['Execution Time'] for p in before],after_ms=[p['Execution Time'] for p in after],
                        before_median_ms=b,after_median_ms=a,observed_ratio=round(b/a,2),results_equal=True,
                        matching_lines=sum(row[1] for row in after_rows),before_plans=before,after_plans=after)
        finally:
            conn.rollback()
            conn.execute(sql.SQL('drop schema if exists {} cascade').format(sql.Identifier(schema)))
            conn.commit()
    result['elapsed_seconds']=round(time.monotonic()-started,2)
    result['temporary_schema_removed']=True
    (ROOT/'docs/gold_index_benchmark.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    (ROOT/'docs/gold_index_benchmark.md').write_text(f'''# Gold index experiment

On isolated copies of all {result['copied_line_rows']:,} professional line join columns
and {result['copied_member_rows']:,} members, run a provider/year filter joined to members
and grouped by sex. Choose the most frequent rendering NPI deterministically.

- Before indexes: median **{b:.3f} ms** across three measured runs.
- After indexes: median **{a:.3f} ms** across three measured runs.
- Same query results: **{result['matching_lines']:,} matching lines**, identical sums.
- Added B-tree indexes on `(rendering_npi, service_dt)` and unique `(member_key)`.

Each condition had one warm-up. Planner choices were not forced. This is one
local, selective-query experiment with warm caches and narrower copied tables;
it does not establish a production speedup or a benefit for every query.
Bulk aggregations may still appropriately use sequential scans. Existing gold
indexes were not removed. The temporary benchmark schema was removed afterward.

See [all timings and EXPLAIN plans](gold_index_benchmark.json).
''')
    print(f'Before median {b:.3f}ms; after {a:.3f}ms; equal results; temporary schema removed.')


if __name__=='__main__':main()
