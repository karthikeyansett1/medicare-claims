"""Independent Python panel aggregation and ranking against warehouse sources."""
import json
from collections import defaultdict
from decimal import Decimal
from psycopg.rows import dict_row
from ingest.db import get_conn, ROOT


def main():
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            def rows(sql):
                cur.execute(sql)
                return cur.fetchall()
            costs = {r['member_year_key']: r for r in rows('select * from gold.fct_member_year_cost where year in (2009,2010)')}
            expected = {r['member_year_key']: r for r in rows('select * from analysis.expected_cost')}
            months = {r['member_year_key']: r['required_months'] for r in rows('select member_year_key,required_months from gold.dim_member_year')}
            admissions = defaultdict(int)
            for r in rows('select member_key,extract(year from admit_dt)::integer as year from gold.int_stays_merged where valid_dates'):
                admissions[r['member_key'],r['year']] += 1
            readmits = defaultdict(lambda: [0,0])
            for r in rows('select member_key,year,is_readmit_30d from gold.fct_readmissions where is_index_eligible'):
                readmits[r['member_key'],r['year']][0] += 1
                readmits[r['member_key'],r['year']][1] += int(r['is_readmit_30d'])
            panels = defaultdict(lambda: defaultdict(lambda: Decimal(0)))
            for a in rows('select * from gold.attribution_long where attributed_npi is not null'):
                p = panels[a['_sample_id'],a['attributed_npi'],a['year'],a['method']]
                key = a['member_year_key']; c = costs[key]
                p['panel_size'] += 1; p['member_months'] += months[key]
                for name in ('medical_paid_amt','rx_gross_cost_amt','ed_claim_count'):
                    p[name] += c[name]
                p['expected_medical_paid_amt'] += Decimal(str(expected[key]['expected_medical_paid_amt']))
                p['admissions'] += admissions[a['member_key'],a['year']]
                ix,rd = readmits[a['member_key'],a['year']]
                p['index_stays'] += ix; p['readmissions'] += rd
            actual = {(r['_sample_id'],r['attributed_npi'],r['year'],r['method']): r for r in rows('select * from marts.mart_provider_performance')}
    assert panels.keys() == actual.keys()
    checks = 0
    for key,p in panels.items():
        p['medical_pmpm'] = p['medical_paid_amt']/p['member_months']
        p['rx_gross_pmpm'] = p['rx_gross_cost_amt']/p['member_months']
        p['admissions_per_1000'] = p['admissions']*12000/p['member_months']
        p['ed_claims_per_1000'] = p['ed_claim_count']*12000/p['member_months']
        p['oe_ratio'] = p['medical_paid_amt']/p['expected_medical_paid_amt']
        for name,val in p.items():
            assert abs(Decimal(str(actual[key][name]))-val) < Decimal('0.00001'), (key,name)
            checks += 1
        assert actual[key]['meets_min_panel'] == (p['panel_size'] >= 20)
        assert actual[key]['readmission_rate'] == (None if p['index_stays']==0 else actual[key]['readmission_rate'])
        if p['index_stays']:
            assert abs(actual[key]['readmission_rate']-p['readmissions']/p['index_stays']) < Decimal('1e-15')
        if p['panel_size'] < 20:
            assert all(actual[key][n] is None for n in ('raw_rank','raw_decile','oe_rank','oe_decile'))
    groups = defaultdict(list)
    for k,p in panels.items():
        if p['panel_size'] >= 20:
            groups[k[0],k[2],k[3]].append(k)
    for keys in groups.values():
        for metric,prefix in [('medical_pmpm','raw'),('oe_ratio','oe')]:
            ordered = sorted(keys, key=lambda k:(panels[k][metric],k[1]))
            q,r = divmod(len(ordered),10)
            deciles = [d for d in range(1,11) for _ in range(q+(d<=r))]
            for rank,(key,decile) in enumerate(zip(ordered,deciles),1):
                assert actual[key][prefix+'_rank']==rank
                assert actual[key][prefix+'_decile']==decile
                checks += 2
    report = {'status':'PASS','provider_panels':len(panels),'qualifying_panels':sum(map(len,groups.values())), 'numeric_and_rank_comparisons':checks,
              'groups':[{ 'sample':k[0],'year':k[1],'method':k[2],'qualifying_panels':len(v)} for k,v in sorted(groups.items())]}
    (ROOT/'docs/metrics_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
