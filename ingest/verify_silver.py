"""Read-only, exact-decimal reconciliation from source profile through silver."""
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import yaml
from psycopg import sql

from ingest.db import ROOT, get_conn


def main():
    started = time.monotonic()
    spec = yaml.safe_load((ROOT / 'dbt_project/dbt_project.yml').read_text())['vars']['source_columns']
    profile = json.loads((ROOT / 'docs/data_profile.json').read_text())
    checks = []
    counts = {}

    def check(label, actual, expected):
        checks.append({'check': label, 'actual': str(actual), 'expected': str(expected),
                       'passed': actual == expected})

    def totals(conn, schema, table, columns, raw=False):
        expressions = [sql.SQL('count(*)')]
        for c in columns:
            ident = sql.Identifier(c['source'] if raw else c['name'])
            expr = sql.SQL("nullif(btrim({}), '')::numeric").format(ident) if raw else ident
            expressions.append(sql.SQL('coalesce(sum({}),0)').format(expr))
        return conn.execute(sql.SQL('select {} from {}.{}').format(
            sql.SQL(',').join(expressions), sql.Identifier(schema), sql.Identifier(table))).fetchone()

    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read read only')
        for table, cols in spec.items():
            numbers = [c for c in cols if c['kind'] == 'numeric']
            bronze = totals(conn, 'bronze', table, numbers, raw=True)
            stage = totals(conn, 'staging', 'stg_' + table, numbers)
            counts['stg_' + table] = stage[0]
            expected_files = [v for k,v in profile['files'].items() if k.startswith(table)]
            check(table + '.profile_rows', bronze[0], sum(v['rows'] for v in expected_files))
            check(table + '.staging_rows', stage[0], bronze[0])
            for c, before, after in zip(numbers, bronze[1:], stage[1:]):
                check(table + '.' + c['name'] + '.bronze_to_staging', after, before)
                for v in expected_files:
                    if c['source'].upper() in v['money']:
                        # Profile sums are per file; accumulate below once per column.
                        break
                else:
                    continue
                check(table + '.' + c['name'] + '.profile_to_staging', after,
                      sum(Decimal(v['money'][c['source'].upper()]['total_cents']) / 100
                          for v in expected_files))
            print('Verified bronze/profile -> staging:', table, flush=True)

        for model in ['silver_carrier_lines','silver_diagnoses','silver_inpatient_stays',
                      'silver_outpatient_claims','silver_member_months','silver_pde_fills']:
            counts[model] = conn.execute(sql.SQL('select count(*) from silver.{}').format(sql.Identifier(model))).fetchone()[0]
        for kind, model in [('inpatient','silver_inpatient_stays'),('outpatient','silver_outpatient_claims')]:
            expected = conn.execute(sql.SQL('select count(*) from (select distinct _sample_id,member_id,claim_id from staging.{}) c').format(sql.Identifier('stg_' + kind))).fetchone()[0]
            check(model + '.claim_grain', counts[model], expected)
            expected_money = conn.execute(sql.SQL('select sum(paid_amt) from staging.{}').format(sql.Identifier('stg_' + kind))).fetchone()[0]
            actual_money = conn.execute(sql.SQL('select sum(paid_amt) from silver.{}').format(sql.Identifier(model))).fetchone()[0]
            check(model + '.paid_amt', actual_money, expected_money)
        for col in ['gross_drug_cost_amt','patient_pay_amt']:
            before = conn.execute(sql.SQL('select sum({}) from staging.stg_pde').format(sql.Identifier(col))).fetchone()[0]
            after = conn.execute(sql.SQL('select sum({}) from silver.silver_pde_fills').format(sql.Identifier(col))).fetchone()[0]
            check('pde.' + col, after, before)
        check('pde.rows', counts['silver_pde_fills'], counts['stg_pde'])
        check('beneficiary.rows', counts['silver_member_months'], counts['stg_beneficiary'])
        for prefix, out in [('line_nch_pmt_amt','line_paid_amt'),('line_alowd_chrg_amt','line_allowed_amt'),
                            ('line_bene_ptb_ddctbl_amt','line_deductible_amt'),
                            ('line_bene_prmry_pyr_pd_amt','line_primary_payer_amt'),
                            ('line_coinsrnc_amt','line_coinsurance_amt')]:
            terms = sql.SQL('+').join(sql.SQL('coalesce({},0)').format(sql.Identifier(f'{prefix}_{n}')) for n in range(1,14))
            before = conn.execute(sql.SQL('select sum({}) from staging.stg_carrier').format(terms)).fetchone()[0]
            after = conn.execute(sql.SQL('select sum({}) from silver.silver_carrier_lines').format(sql.Identifier(out))).fetchone()[0]
            check('carrier.' + out, after, before)
        carrier_profiles = [v for k,v in profile['files'].items() if k.startswith('carrier')]
        check('carrier.active_slots', counts['silver_carrier_lines'], sum(v['quirks']['active_line_slots'] for v in carrier_profiles))
        missing = conn.execute('select count(*) filter(where line_paid_amt <> 0), sum(line_paid_amt) from silver.silver_carrier_lines where missing_hcpcs').fetchone()
        check('carrier.paid_slots_without_hcpcs', missing[0], sum(v['quirks']['nonzero_paid_missing_hcpcs'] for v in carrier_profiles))
        check('carrier.paid_without_hcpcs', missing[1], sum(Decimal(v['quirks']['paid_cents_missing_hcpcs']) / 100 for v in carrier_profiles))
        expected_dx = 0
        for table,n in [('inpatient',10),('outpatient',10),('carrier',8)]:
            terms = sql.SQL('+').join(sql.SQL('count({})').format(sql.Identifier(f'icd9_dgns_cd_{i}')) for i in range(1,n+1))
            expected_dx += conn.execute(sql.SQL('select {} from staging.{}').format(terms,sql.Identifier('stg_'+table))).fetchone()[0]
        check('diagnoses.nonblank_positions', counts['silver_diagnoses'], expected_dx)
        audit = conn.execute('select source_table,_source_file,source_rows,rows_with_cast_errors,cast_error_values from silver.silver_cast_audit order by 1,2').fetchall()
        counts['silver_cast_audit'] = len(audit)
        check('safe_cast_errors', sum(row[4] for row in audit), 0)
        flags = {}
        for model in ['silver_inpatient_stays','silver_outpatient_claims']:
            fields = ['has_header_conflict','repeated_equal_payment','has_negative_payment']
            if model.endswith('claims'): fields.append('is_ed_visit')
            row = conn.execute(sql.SQL('select {} from silver.{}').format(sql.SQL(',').join(
                sql.SQL('count(*) filter(where {})').format(sql.Identifier(c)) for c in fields), sql.Identifier(model))).fetchone()
            flags[model] = dict(zip(fields,row))
        eligibility = conn.execute('select year,count(*),count(*) filter(where is_full_year_ffs),count(*) filter(where is_ffs_eligible) from silver.silver_member_months group by year order by year').fetchall()

    result = {'verified_at_utc':datetime.now(timezone.utc).isoformat(),
              'elapsed_seconds':round(time.monotonic()-started,2), 'row_counts':counts,
              'checks':checks, 'all_passed':all(c['passed'] for c in checks),
              'cast_audit':[dict(zip(['table','file','rows','rows_with_errors','error_values'],row)) for row in audit],
              'facility_flags':flags,
              'annual_eligibility':[dict(zip(['year','rows','strict_full_year','death_adjusted_proxy'],row)) for row in eligibility]}
    (ROOT/'docs/silver_reconciliation.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    lines = ['# Silver reconciliation','',f"Verified: {result['verified_at_utc']}",
             f"\nChecks: {sum(c['passed'] for c in checks)}/{len(checks)} passed; exact decimal comparisons.",
             '', '| Model | Rows |','| --- | ---: |']
    lines += [f'| {k} | {v:,} |' for k,v in counts.items()]
    lines += ['', 'Full individual comparisons, cast-error counts, conflict flags, and enrollment',
              'counts are in [the JSON evidence](silver_reconciliation.json).',
              'Financial scopes remain separate: medical Medicare paid, carrier allowed,',
              'drug gross cost, and drug patient payment. No amounts are rounded by safe casts.',
              '', 'This read-only check does not refresh tables. Run `make silver` first after code',
              'changes; the dbt build must pass before treating the checkpoint as complete.']
    (ROOT/'docs/silver_reconciliation.md').write_text('\n'.join(lines)+'\n')
    print(f"{sum(c['passed'] for c in checks)}/{len(checks)} checks passed in {result['elapsed_seconds']}s")
    if not result['all_passed']:
        raise SystemExit('Reconciliation failed: '+', '.join(c['check'] for c in checks if not c['passed']))


if __name__ == '__main__':
    main()
