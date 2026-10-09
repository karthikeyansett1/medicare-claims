"""Independently reconcile gold facts and every member-year without fact-to-fact joins."""
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

import yaml
from psycopg import sql

from ingest.db import ROOT, get_conn

# SQL reductions are applied separately to each fact. Python combines groups,
# independently of the UNION implementation in the dbt summary model.
MEASURES = {
    'fct_inpatient_stays': ('service_dt', {
        'inpatient_paid_amt': 'coalesce(sum(paid_amt),0)',
        'inpatient_claim_episode_count': 'count(*)',
        'missing_medical_payment_count': 'sum(missing_payment_segments)'}),
    'fct_outpatient_claims': ('service_dt', {
        'outpatient_paid_amt': 'coalesce(sum(paid_amt),0)',
        'outpatient_claim_count': 'count(*)',
        'ed_claim_count': 'count(*) filter(where is_ed_visit)',
        'missing_medical_payment_count': 'sum(missing_payment_segments)'}),
    'fct_professional_lines': ('service_dt', {
        'professional_paid_amt': 'coalesce(sum(paid_amt),0)',
        'professional_allowed_amt': 'coalesce(sum(allowed_amt),0)',
        'professional_line_count': 'count(*)',
        'office_em_line_count': 'count(*) filter(where is_office_em)',
        'missing_medical_payment_count': 'count(*) filter(where paid_amt is null)'}),
    'fct_rx_fills': ('fill_dt', {
        'rx_gross_cost_amt': 'coalesce(sum(gross_drug_cost_amt),0)',
        'rx_patient_pay_amt': 'coalesce(sum(patient_pay_amt),0)',
        'rx_fill_count': 'count(*)',
        'missing_rx_gross_cost_count': 'count(*) filter(where gross_drug_cost_amt is null)'})}
SOURCE_PAIRS = [
    ('silver_carrier_lines','fct_professional_lines', ['line_paid_amt','line_allowed_amt'],['paid_amt','allowed_amt']),
    ('silver_inpatient_stays','fct_inpatient_stays',['paid_amt'],['paid_amt']),
    ('silver_outpatient_claims','fct_outpatient_claims',['paid_amt'],['paid_amt']),
    ('silver_pde_fills','fct_rx_fills',['gross_drug_cost_amt','patient_pay_amt'],['gross_drug_cost_amt','patient_pay_amt'])]


def main():
    start = time.monotonic()
    checks, counts, index_report, financial_totals = [], {}, {}, {}

    def check(name, actual, expected):
        checks.append(dict(check=name,actual=str(actual),expected=str(expected),passed=actual==expected))

    schema = yaml.safe_load((ROOT/'dbt_project/models/gold/schema.yml').read_text())
    spec = {m['name']:m for m in schema['models']}
    manifest = json.loads((ROOT/'dbt_project/target/manifest.json').read_text())
    expected = defaultdict(lambda: defaultdict(Decimal))
    enrollment = {}
    date_assignments = {}
    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read read only')
        for name, definition in spec.items():
            counts[name] = conn.execute(sql.SQL('select count(*) from gold.{}').format(sql.Identifier(name))).fetchone()[0]
            actual_columns = {r[0] for r in conn.execute(
                "select column_name from information_schema.columns where table_schema='gold' and table_name=%s", (name,))}
            documented_columns = {c['name'] for c in definition['columns'] if c.get('description')}
            check(name+'.documented_columns', sorted(documented_columns), sorted(actual_columns))
            definitions = [r[0] for r in conn.execute(
                "select indexdef from pg_indexes where schemaname='gold' and tablename=%s order by indexname", (name,))]
            index_report[name] = definitions
            configured = manifest['nodes']['model.medicare.'+name]['config']['indexes']
            actual_indexes = conn.execute('''select i.indisunique, i.indisvalid and i.indisready,
              array(select a.attname from unnest(i.indkey) with ordinality k(attnum,pos)
              join pg_attribute a on a.attrelid=i.indrelid and a.attnum=k.attnum order by k.pos)
              from pg_index i join pg_class t on t.oid=i.indrelid
              join pg_namespace n on n.oid=t.relnamespace where n.nspname='gold' and t.relname=%s''',(name,)).fetchall()
            for index in configured:
                want=(bool(index.get('unique',False)),True,index['columns'])
                check(name+'.index.'+','.join(index['columns']),want in actual_indexes,True)
        for src,dst,src_cols,dst_cols in SOURCE_PAIRS:
            before = conn.execute(sql.SQL('select count(*),{} from silver.{}').format(
                sql.SQL(',').join(sql.SQL('sum({})').format(sql.Identifier(c)) for c in src_cols),sql.Identifier(src))).fetchone()
            date_col = sql.Identifier(MEASURES[dst][0])
            after = conn.execute(sql.SQL('''select count(*),{},
                count(*) filter(where {} is null),
                count(*) filter(where {} < date '2008-01-01' or {} > date '2010-12-31')
                from gold.{}''').format(
                sql.SQL(',').join(sql.SQL('sum({})').format(sql.Identifier(c)) for c in dst_cols),
                date_col,date_col,date_col,sql.Identifier(dst))).fetchone()
            date_assignments[dst] = dict(missing_service_dates=after[-2],outside_analysis_window=after[-1])
            check(dst+'.source_rows',after[0],before[0])
            for col,a,b in zip(dst_cols,after[1:],before[1:]):
                check(dst+'.'+col,a,b);financial_totals[dst+'.'+col]=str(a)
        for row in conn.execute('select _sample_id,member_id,year,member_year_key from gold.dim_member_year'):
            key=tuple(row[:3]); enrollment[key]=row[3];expected[key]
        for model,(date,measures) in MEASURES.items():
            query=sql.SQL('select _sample_id,member_id,extract(year from {})::int,{} from gold.{} group by 1,2,3').format(
                sql.Identifier(date),sql.SQL(',').join(sql.SQL(v) for v in measures.values()),sql.Identifier(model))
            for row in conn.execute(query):
                for col,value in zip(measures,row[3:]):expected[tuple(row[:3])][col]+=Decimal(value or 0)
            print('Independently aggregated:',model,flush=True)
        names=list(dict.fromkeys(c for _,measures in MEASURES.values() for c in measures))
        query=sql.SQL('select _sample_id,member_id,year,member_year_key,has_annual_enrollment,medical_paid_amt,{} from gold.fct_member_year_cost').format(sql.SQL(',').join(map(sql.Identifier,names)))
        mismatches=0;seen=set();comparison_count=0
        for row in conn.execute(query):
            key=tuple(row[:3]);seen.add(key)
            if key not in expected:mismatches+=1;continue
            values=expected[key]
            wanted_medical=sum(values[c] for c in ['inpatient_paid_amt','outpatient_paid_amt','professional_paid_amt'])
            wanted=[enrollment.get(key),key in enrollment,wanted_medical]+[values[c] for c in names]
            for actual,want in zip(row[3:],wanted):
                comparison_count+=1
                if actual!=want:mismatches+=1
        check('member_year.group_keys',len(seen.symmetric_difference(expected)),0)
        check('member_year.individual_measure_mismatches',mismatches,0)
        check('member_year.row_count',counts['fct_member_year_cost'],len(expected))
        profile=json.loads((ROOT/'docs/data_profile.json').read_text())
        check('dim_member.members',counts['dim_member'],profile['files']['beneficiary_2008']['rows'])
        check('dim_member_year.rows',counts['dim_member_year'],sum(v['rows'] for k,v in profile['files'].items() if k.startswith('beneficiary')))
        calendar=conn.execute('select min(date),max(date),count(*) filter(where is_analysis_window) from gold.dim_date').fetchone()
        check('calendar.analysis_days',calendar[2],1096)
        extras=conn.execute('select year,count(*),sum(medical_paid_amt),sum(rx_gross_cost_amt) from gold.fct_member_year_cost where not has_annual_enrollment group by year order by year nulls last').fetchall()
        members_no_cost=conn.execute('select count(*) from gold.fct_member_year_cost where professional_line_count+inpatient_claim_episode_count+outpatient_claim_count+rx_fill_count=0').fetchone()[0]
        provider_stats=conn.execute('select count(*),sum(total_lines_billed),count(*) filter(where is_em_provider),count(*) filter(where seen_as_inpatient_attending and not seen_as_rendering) from gold.dim_provider').fetchone()
        known_rendering=conn.execute('select count(*) from gold.fct_professional_lines where rendering_npi is not null').fetchone()[0]
        check('provider.line_counts',provider_stats[1],known_rendering)
        em=conn.execute('select count(*) from gold.fct_professional_lines where is_office_em').fetchone()[0]
        missing_paid=conn.execute('select sum(paid_amt) from gold.fct_professional_lines where missing_hcpcs').fetchone()[0]
        check('carrier.missing_hcpcs_paid',missing_paid,Decimal('20695070'))
        # Check the materialized seed too, not just its local copy.
        seeded=[r[0] for r in conn.execute('select hcpcs_cd from reference.em_office_visit_codes order by hcpcs_cd')]
        check('em_seed.codes',seeded,[str(c) for c in list(range(99201,99206))+list(range(99211,99216))])
    original=(ROOT/'data/reference/em_office_visit_codes.csv').read_bytes()
    copied=(ROOT/'dbt_project/seeds/em_office_visit_codes.csv').read_bytes()
    check('em_seed.source_bytes',hashlib.sha256(copied).hexdigest(),hashlib.sha256(original).hexdigest())
    result=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-start,2),
                all_passed=all(c['passed'] for c in checks),checks=checks,row_counts=counts,
                member_year_field_comparisons=comparison_count,financial_totals=financial_totals,indexes=index_report,
                date_assignments=date_assignments,
                calendar=dict(first_date=str(calendar[0]),last_date=str(calendar[1]),analysis_days=calendar[2]),
                without_annual_enrollment=[dict(year=row[0],member_years=row[1],medical_paid=str(row[2]),rx_gross_cost=str(row[3])) for row in extras],
                enrollment_years_without_claim_events=members_no_cost,
                provider_summary=dict(providers=provider_stats[0],known_npi_lines=int(provider_stats[1]),em_providers=provider_stats[2],attending_only=provider_stats[3]),
                office_em_lines=em)
    (ROOT/'docs/gold_reconciliation.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    lines=['# Gold reconciliation','',f"Verified {result['verified_at_utc']}",'',
           f"Checks: {sum(c['passed'] for c in checks)}/{len(checks)} passed.",
           f'Independently compared {comparison_count:,} member-year fields without fact-to-fact joins.','',
           '| Model | Rows |','| --- | ---: |']
    lines += [f'| {k} | {v:,} |' for k,v in counts.items()]
    lines += ['', 'See [JSON evidence](gold_reconciliation.json) for individual checks, financial scopes,',
              'indexes, outside-enrollment years, and the calendar range. Prescription gross cost',
              'is never labeled Medicare paid. These are local Sample 1 checks.']
    (ROOT/'docs/gold_reconciliation.md').write_text('\n'.join(lines)+'\n')
    print(f"{sum(c['passed'] for c in checks)}/{len(checks)} checks; {comparison_count:,} member-year comparisons; {result['elapsed_seconds']}s")
    if not result['all_passed']:raise SystemExit('Gold reconciliation failed: '+', '.join(c['check'] for c in checks if not c['passed']))


if __name__=='__main__':main()
